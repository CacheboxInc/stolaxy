from xdrdef.nfs3_const import *
from xdrdef.nfs3_type import *
from config import *
from ctypes import *

import xdrdef.nfs3_pack
import rpc.rpc
import os, time, array, random, string
try:
    import cStringIO
    StringIO = cStringIO
except:
    import StringIO

import logging
from stat import *
import sha
import shutil
import zlib

logger = logging.getLogger('nfslog')

from args import args as sargs

cdll.LoadLibrary("libc.so.6")
libc = CDLL("libc.so.6")

inodecount = 0
generationcount = 0

InstanceKey = string.join([random.choice(string.ascii_letters) for x in range(4)], "")
def Mutate():
    global InstanceKey
    InstanceKey = string.join([random.choice(string.ascii_letters) for x in range(4)], "")


POSIXLOCK = True # If True, allow locks to be split/joined automatically
POSIXACL = True # If True, forces acls to follow posix mapping rules

class NFS3Error(Exception):
    def __init__(self, code, msg=None, attrs=0L, lock_denied=None):
        self.code = code
        self.name = nfsstat3[code]
        if msg is None:
            self.msg = "NFS3 error code: %s" % self.name
        else:
            self.msg = str(msg)
        self.attrs = attrs
        self.lock_denied = lock_denied

    def __str__(self):
        return self.msg

def mod32(number):
    # int(number%0x100000000) doesn't work, since int is signed, we only
    # have 31 bits to play with
    return number % 0x100000000

def converttime(now=None):
    """Return time in nfstime3 format"""
    if now is None:
        now = time.time()
    sec = int(now)
    nsec = (now-sec) * 1000000000
    return nfstime3(sec, nsec)

def packnumber(number, size=NFS3_CREATEVERFSIZE, factor=1):
    """Return a string of length size which holds bitpacked number

    If result will not fit, the high bits are truncated.
    """
    numb = long(number * factor)
    bytes = array.array('B')
    for i in range(size):
        bytes.append(0)
    # i == size - 1
    while numb > 0 and i >= 0:
        bytes[i] = numb % 256
        numb /= 256
        i -= 1
    return bytes.tostring()

def unpacknumber(str):
    """Return number associated with bitpacked string"""
    numb = 0
    for c in str:
        numb = 256 * numb + ord(c)
    return numb

def printverf(verifier):
    """Returns a printable version of a 'binary' string"""
    str = ""
    for c in verifier:
        str += "%x" % ord(c)
    return str

#########################################################################


class NFSFileState:
    """Holds file state info"""
    def __init__(self):
        self.locks = {}  # form {id: [LockInfo, ...]}
        self.shares = {} # form {id : [3bit_access, 3bit_deny]}
        self.access = 0  # Use external 2-bit format
        self.deny = 0    # Use external 2-bit format

    class LockInfo:
        def __init__(self, type, start, end):
            self.type = type # bit 0:  0=WRITE 1=READ
            self.start = start
            self.end = end
            if start < 0 or end < start:
                raise ValueError, "Bad values for start and end (%s, %s)" % \
                                  (start, end)

        def __repr__(self):
            if self.type & 1: str = "READ"
            else: str = "WRITE"
            return "%sLOCK: %i to %i" % (str, self.start, self.end)

        def __cmp__(self, other):
            if type(other) == type(5):
                other = self.LockInfo(0, other, self.end)
            if not isinstance(other, NFSFileState.LockInfo):
                return NotImplemented
            if self.start < other.start: return -1
            elif self.start > other.start: return 1
            elif self.end < other.end: return -1
            elif self.end > other.end: return 1
            else: return 0

        def overlaps(self, start, end):
            """Returns True if given range overlaps that of lock"""
            return start <= self.start <= end or \
                   self.start <= start <= self.end

    def __2to3(self, value):
        """Change 2 bit external value to 3 bit internal"""
        value &= 3
        if value: return 2 ** (value-1)
        else: return 0

    def __3to2(self, value):
        """Change 3 bit internal value to 2 bit external"""
        if value & 4: return 3
        else: return value & 3
        
    def downshares(self, id, access, deny):
        """Downgrade shares.  access == deny == 0 removes shares completely"""
        if id not in self.shares:
            if access != 0 or deny != 0:
                raise "Unknown id"
            else:
                return
        old_access = self.shares[id][0]
        old_deny = self.shares[id][1]
        new_access = self.__2to3(access)
        new_deny = self.__2to3(deny)
        if new_access & ~old_access or new_deny & ~old_deny:
            raise NFS3Error(NFS3ERR_INVAL)
        if access == 0 and deny != 0:
            raise "Invalid values"
        # Set new value for id
        if access == 0 and deny == 0:
            del self.shares[id]
        else:
            self.shares[id] = [new_access, new_deny]
        # Adjust files overall values
        new_access = new_deny = 0
        for i in self.shares:
            new_access |= self.shares[i][0]
            new_deny |= self.shares[i][1]
        self.access = self.__3to2(new_access)
        self.deny = self.__3to2(new_deny)

    def addshares(self, id, access, deny):
        """Add given shares, after checking for conflicts."""
        self.testshares(access, deny)
        self.access |= access
        self.deny |= deny
        if id not in self.shares:
            self.shares[id] = [0,0]
        self.shares[id][0] |= self.__2to3(access)
        self.shares[id][1] |= self.__2to3(deny)

    def testshares(self, access, deny):
        """Raises NFS3Error if proposed shares conflict with existing"""
        if access == 0:
            raise NFS3Error(NFS3ERR_INVAL)
        if access & self.deny or deny & self.access:
            raise NFS3Error(NFS3ERR_ACCES)

    def checkaccess(self, id, mode):
        """Raise erropr if owner id cannot access file with mode"""
        if id not in [0,1]:
            try:
                if self.__3to2(self.shares[id][0]) & mode != mode:
                    raise NFS3Error(NFS3ERR_ACCES)
            except KeyError:
                raise NFS3Error(NFS3ERR_STALE)
        if mode & self.deny:
            # Can get here if use reserved stateid
            raise NFS3Error(NFS3ERR_ACCES)

    def removelocks(self, id):
        """Remove all locks for given id"""
        if id in self.locks:
            del self.locks[id]

    def addlock(self, id, type, start, end):
        """Add lock, assuming we have already tested for no conflicts"""
        if id not in self.locks:
            # Simple case of no previous lock by this owner
            self.locks[id] = [self.LockInfo(type, start, end)]
            return
        if POSIXLOCK:
            self.addposixlock(self.locks[id], type, start, end)
            return
        # Handle nonPOSIX locks
        for lock in self.locks[id]:
            if lock.overlaps(start, end):
                if lock.start==start and lock.end==end:
                    #Up/downgrade existing lock
                    lock.type = type
                    return
                else:
                    raise NFS3Error(NFS3ERR_BADTYPE)
        self.locks[id].append(self.LockInfo(type, start, end))

    def testlock(self, ids, type, start, end):
        """See if lock conflicts with owners not in 'ids' list

        Returns info on the conflicting lock if found, None otherwise.
        """
        for owner in self.locks:
            if owner in ids: continue
            for lock in self.locks[owner]:
                if lock.overlaps(start, end) and (type&1==0 or lock.type&1==0):
                    return (owner, lock)
        return None

    def unlock(self, id, type, start, end):
        """Remove a lock"""
        if id not in self.locks:
            return
        if POSIXLOCK:
            self.removeposixlock(self.locks[id], type, start, end)
            return
        # Handle nonPOSIX locks
        for i,lock in zip(range(len(self.locks[id])), self.locks[id]):
            if lock.overlaps(start, end):
                if lock.start == start and lock.end == end:
                    del self.locks[id][i]
                    if len(self.locks[id]) == 0:
                        del self.locks[id]
                    return
                else:
                    raise NFS3Error(NFS3ERR_BADTYPE)
        return

    def addposixlock(self, list, type, start, end):
        """Adds lock to list, splitting/merging existing locks as necessary"""
        self.__removerange(list, start, end)
        list.append(self.LockInfo(type, start, end))
        list.sort()
        # Merge adjacent locks
        for i in range(len(list) - 1, 0, -1):
            if list[i].start == list[i-1].end + 1 and \
               list[i].type == list[i-1].type:
                  list[i-1].end = list[i].end
                  del list[i]
        logger.info(list)

    def removeposixlock(self, list, type, start, end):
        """Removes lock from sorted list, splitting existing locks as necessary
        """
        self.__removerange(list, start, end)
        list.sort()
        logger.info(list)

    def __removerange(self, list, start, end):
        """Removes locks in given range, shrinking locks that half-overlap"""
        # If start is inside a lock, we split that lock in two
        for lock in list:
            if lock.start < start <= lock.end:
                list.append(self.LockInfo(lock.type, start, lock.end))
                lock.end = start - 1
                break
        # If end is inside a lock, we split that lock in two
        for lock in list:
            if lock.start <= end < lock.end:
                list.append(self.LockInfo(lock.type, lock.start, end))
                lock.start = end + 1
                break
        # Remove all locks inside given range
        for lock in list[:]:
            if lock.overlaps(start, end):
                list.remove(lock)
        
#########################################################################

class NFSFileHandle(object):
    # name = the external NFS3 name
    # file = the real, local file
    # parent = the parent directory, None if root.
    def __init__(self, name, parent):
        global InstanceKey
        # Note: name should be removed, since hardlinking makes it unknowable
        self.name = name
        self.handle = InstanceKey + self.get_fhclass() + sha.new(self.name+str(time.time())).hexdigest() + "\x00\x00\x00\x00"
        self.fattr3_change = 0
        self.lock_status = {}
        self.parent = parent
        self.write_verifier = packnumber(time.time())

    def find(self, file):
        # search through the filesystem for a filename
        raise "implement find."

    #def __repr__(self):
    #    return "<NFSFileHandle(%s): %s>" % (self.get_fhclass(), str(self.file))
    
    def __str__(self):
        return self.name

    def supported_access(self, client):
        raise "Implement supported_access()"
        
    def evaluate_access(self, client):
        raise "Implement evaluate_access()"

    def get_attributes(self, attrlist=None):
        raise "Implement get_attributes"
                
    def get_directory(self):
        raise "Implement get_directory"                

    def get_type(self):
        raise "Implement get_type"
    
    def read(self, offset, count):
        raise "Implement read"

    def write(self, offset, data):
        raise "Implement write"
        
    def link(self, target):
        raise "Implement link"

    def destruct(self):
        raise "Implement destruct"

    def remove(self, target):
        raise "implement remove"

def handle(*args):
    """
    implements class factory
    """
    if htype == 'HARD_HANDLE':
        return HardHandle(*args)
    elif htype == 'NULL_HANDLE':
        return NULLHandle(*args)
    elif htype == 'REPLICA_HANDLE':
        return ReplicaHandle(*args)

    assert 0, 'unknown htype: %s' % htype
    

class HardHandle(NFSFileHandle):

    def __init__(self, filesystem, name, parent, file):
        NFSFileHandle.__init__(self, name, parent)
        self.file = file
        self.mtime = 0
        self.fh = self
        self.cookie = 0
        self.dirent = {}

        self.link_filehandle = None
        self._set_default_attrs()
        self.dirent[name] = self.fh

    supported = {
                 'fattr3_size'        : 'rw', 
                 'fattr3_type'        : 'r', 
                 'fattr3_numlinks'    : 'r',
                 'fattr3_fsid'        : 'r', 
                 'fattr3_fileid'      : 'r', 
                 'fattr3_mode'        : 'rw',
                 'fattr3_rdev'        : 'r', 
                 'fattr3_atime'       : 'rw', 
                 'fattr3_mtime'       : 'rw',
                 'fattr3_ctime'       : 'r', 
                 'fattr3_used'        : 'r', 
                 'fattr3_uid'         : 'rw',
                 'fattr3_gid'         : 'rw', 
                 'fattr3_rtmax'       : 'r', 
                 'fattr3_rtpref'      : 'r',
                 'fattr3_dtpref'      : 'r', 
                 'fattr3_maxfilesize' : 'r', 
                 'fattr3_time_delta'  : 'r',
                 'fattr3_properties'  : 'r'
                }
                 

    def _set_default_attrs(self):
        stat_struct = os.lstat(self.file)
        self.stat_struct = stat_struct
        if S_ISDIR(stat_struct.st_mode):
            self.fattr3_type = NF3DIR
        elif S_ISREG(stat_struct.st_mode):
            self.fattr3_type = NF3REG
        elif S_ISLNK(stat_struct.st_mode):
            self.fattr3_type = NF3LNK
        self.fattr3_size = stat_struct.st_size
        self.fattr3_numlinks = stat_struct.st_nlink
        self.fattr3_fsid = 0
        self.fattr3_fileid = stat_struct.st_ino
        self.fattr3_mode = 644 # Currently no access restrictions enforced
        self.fattr3_rdev = specdata3(os.major(self.stat_struct.st_dev), os.minor(self.stat_struct.st_dev))
        self.fattr3_atime = converttime(self.stat_struct.st_atime)
        self.fattr3_mtime = converttime(self.stat_struct.st_mtime)
        self.fattr3_ctime = converttime(self.stat_struct.st_ctime)
        self.fattr3_used = 0
        self.fattr3_uid = self.stat_struct.st_uid
        self.fattr3_gid = self.stat_struct.st_gid
        self.fattr3_rtmax = 1 << 20
        self.fattr3_rtpref = 1 << 20
        self.fattr3_rtmult = 1
        self.fattr3_wtmax = 1 << 20
        self.fattr3_wtpref = 1 << 20
        self.fattr3_wtmult = 1
        self.fattr3_dtpref = 32 << 10
        self.fattr3_maxfilesize = 1 << 40
        self.fattr3_time_delta = nfstime3(0, 1000000)
        self.fattr3_properties = FSF3_HOMOGENEOUS

    def get_fattr3_attributes(self):
        ret_attr = {}
        for attr in supported.keys():
            try:
                get_funct = getattr(self, "get_" + attr)
                ret_dict[attr] = get_funct()
            except AttributeError:
                ret_dict[attr] = getattr(self, attr)
 
        return ret_attr

    def set_fattr3_size(self, newsize):
        if self.fattr3_type == NF3REG and (newsize != self.fattr3_size or newsize == 0):
            if newsize <= self.fattr3_size:
                fd = os.open(self.file, os.O_RDWR)
                os.ftruncate(fd, newsize)
                os.close(fd)
            else:
                # Pad with zeroes
                fd = os.open(self.file, os.O_RDWR)
                size = newsize - self.fattr3_size
                sz = libc.pwrite(fd, chr(0) * size, size, self.fattr3_size)
                os.close(fd)
            self.fattr3_size = newsize
            self.fattr3_time_modify = converttime()
        else:
            raise NFS3Error(NFS3ERR_INVAL)

    def set_fattr3_attributes(self, attrdict=None):
        ret_list = []
        for attr in attrdict.keys():
            if not self.supported.has_key(attr):
                raise NFS3Error(NFS3ERR_BADTYPE, attrs=ret_list)
            if 'w' not in self.supported[attr]:
                raise NFS3Error(NFS3ERR_INVAL, attrs=ret_list)

            name = attr
            try:
                # Use set function, if it exists
                set_funct = getattr(self, "set_" + name)
                set_funct(attrdict[attr])
            except AttributeError:
                # Otherwise, just set the variable
                setattr(self, name, attrdict[attr])
            except NFS3Error, e:
                # Note attributes set so far in any error that occurred
                e.attrs = ret_list
                raise
            self.fattr3_time_metadata = converttime()
            ret_list.append(attr)
        return ret_list


    def lookup(self, name):
        """ Assume we are a dir, and see if name is one of our files.

        If yes, return it.  If no, return None
        """
        logger.info(('lookup:%s' % name).center(80, '-'))
        if self.fattr3_type != NF3DIR:
            raise "lookup called on non directory."
        try: 
            if self.dirent.has_key(name):
                return self.dirent[name]
            fullfile = os.path.join(self.file, name)
            if not os.path.exists(fullfile):
                return None
            fh = handle(None, name, self, fullfile)
            self.dirent[name] = fh
            return fh
        except KeyError:
            return None

    def do_lookupp(self):
        return self.parent

    def evaluate_access(self):
        return self.supported_access()

    def supported_access(self):
        # page 140 lists that supported should be what the server can verify
        # reliably on the current_filehandle, so I suppose this should depend
        # on the file type
        if self.fattr3_type == NF3DIR:
            # according to page 142, UNIX does not aupport ACCESS3_DELETE on a file
            # however, we will.
            return ACCESS3_READ | ACCESS3_LOOKUP | ACCESS3_MODIFY | ACCESS3_EXTEND | ACCESS3_DELETE
#        elif self.fattr3_type == NF3REG:
            #
        else:
            return ACCESS3_READ | ACCESS3_LOOKUP | ACCESS3_MODIFY | ACCESS3_EXTEND | ACCESS3_DELETE | ACCESS3_EXECUTE

    def getdirverf(self):
        if self.fattr3_type == NF3DIR:
            self.fattr3_time_access = converttime()
            return packnumber(int(self.stat_struct.st_mtime))
        else:
            raise "getdirverf called on non directory."

    def get_attributes(self, attrlist=None):
        now = time.time()
        stat_struct = os.lstat(self.file)
        self.stat_struct = stat_struct
        ret_dict = {};
        for attr in attrlist:
            if attr == FATTR3_TYPE:
                if S_ISDIR(stat_struct.st_mode):
                   ret_dict[attr] = NF3DIR
                elif S_ISREG(stat_struct.st_mode):
                    ret_dict[attr] = NF3REG
                elif S_ISLNK(stat_struct.st_mode):
                    ret_dict[attr] = NF3LNK

                self.fattr3_type = ret_dict[attr]
            else:
                logger.warn(('WARNING: %s not handled' % attr).center(80, '#'))
        return ret_dict

    def get_fhclass(self):
        return "hard"
    
    def get_link(self):
        return os.readlink(self.file)

    def get_type(self):
        stat_struct = os.lstat(self.file)
        if S_ISDIR(stat_struct.st_mode):
            return NF3DIR
        elif S_ISREG(stat_struct.st_mode):
            return NF3REG
        elif S_ISLNK(stat_struct.st_mode):
            return NF3LNK
        else:
            return NF3REG

    def is_empty(self):
        """For a directory, return True if empty, False otherwise"""
        if self.fattr3_type == NF3DIR:
            return len(self.dirent) == 0
        raise "is_empty() called on non-dir"

    def read(self, offset, count):
        if self.fattr3_type != NF3REG:
            raise "read called on non file!"
        fd = os.open(self.file, os.O_RDONLY)
        data = create_string_buffer(count)
        size = libc.pread(fd, data, count, offset)
        os.close(fd)
        self.fattr3_time_access = converttime()
        return data

    def destruct(self):
        # FRED - Note this currently does nothing -
        #      - and should do nothing if link count is positive
        if self.fattr3_numlinks > 0: return
        #print "destructing: %s" % repr(self)
        if self.fattr3_type == NF3DIR:
            for subfile in self.dirent.values():
                subfile.destruct()

    def remove(self, target):
        fullfile = os.path.join(self.file, target)
        if not os.path.exists(fullfile):
            raise "cannot find  file."
        stat_struct = os.stat(fullfile)
        if S_ISDIR(stat_struct.st_mode):
            raise "cannot remove directory"
        elif S_ISLNK(stat_struct.st_mode):
            os.unlink(fullfile) 
        else:
            os.remove(fullfile)

    def rmdir(self, target):
        fullfile = os.path.join(self.file, target)
        if not os.path.exists(fullfile):
            raise "cannot find  file."
        stat_struct = os.stat(fullfile)
        if not S_ISDIR(stat_struct.st_mode):
            raise "not a directory"
        shutil.rmtree(fullfile)

    def __link(self, file, newname):
        if self.fattr3_type != NF3DIR:
             raise "__link called on non-directory"
        return
    
    def rename(self, oldfh, oldname, newname): # self = newfh
        file = oldfh.dirent[oldname]
        old_filefull = os.path.join(oldfh.file, oldname)
        new_filefull = os.path.join(self.file, newname)
        shutil.move(old_filefull, new_filefull)
        fh = handle(None, newname, self, new_filefull)
        self.dirent[newname] = fh
        del self.dirent[oldname]
        file.destruct()

    def read_dir(self, cookie = 0):
        stat_struct = os.stat(self.file)
        if not S_ISDIR(stat_struct.st_mode):
            raise "Not a directory."
        if stat_struct[ST_MTIME] == self.mtime:
            return self.dirent.values()
        self.oldfiles = self.dirent.keys()
        for i in os.listdir(self.file):
            fullfile = os.path.join(self.file, i)
            if not self.dirent.has_key(i):
                self.dirent[i] = handle(None, i, self, fullfile)
            else:
                self.oldfiles.remove(i)
        for i in self.oldfiles:
            del self.dirent[i]
        return self.dirent.values()
        
    def read_link(self):
        return os.readlink(self.file)

    def set_attributes(self, attrdict):
        """Set attributes and return bitmask of those set

        attrdict is of form {bitnum:value}
        For each bitnum, it will try to call self.set_fattr3_<name> if it
        exists, otherwise it will just set the variable self.fattr3_<name>.
        """
        #self.set_fattr3_attributes(attrdict)
        return attrdict

    def create(self, name, mode=UNCHECKED, attrs={}):
        """ Create a file of given type with given attrs, return attrs set

        type is a nfs3types.createtype3 instance
        """
        # Must make sure that if it fails, nothing is changed
        fullfile = os.path.join(self.file, name)
        if os.path.exists(fullfile) and mode == GUARDED:
            raise "attempted to create already existing file."
        fd = os.open(fullfile, os.O_CREAT)
        os.close(fd)
        fh = handle(None, name, self, fullfile)
        attrset = fh.set_attributes(attrs)
        self.dirent[name] = fh
        return attrset

    def mkdir(self, name, attrs={}):
        """ Create a file of given type with given attrs, return attrs set

        type is a nfs3types.createtype3 instance
        """
        # Must make sure that if it fails, nothing is changed
        fullfile = os.path.join(self.file, name)
        if os.path.exists(fullfile):
            raise "attempted to create already existing file."
        os.mkdir(fullfile)
        fh = handle(None, name, self, fullfile)
        attrset = fh.set_attributes(attrs)
        self.dirent[name] = fh
        return attrset

    def write(self, offset, data, count=0, stable=UNSTABLE):
        if self.fattr3_type != NF3REG:
            raise "write called on non file!"
        if len(data) == 0: 
            return 0
        self.fattr3_change += 1

        if count == 0:
            count = len(data)
        fd = os.open(self.file, os.O_RDWR)
        size = libc.pwrite(fd, data, count, offset)
        os.close(fd)
        self.fattr3_size += size
        now = time.time()
        self.fattr3_atime = converttime(now)
        self.fattr3_mtime = converttime(now)
        self.fattr3_ctime = converttime(now)
        return size

    def commit(self, offset, count):
        if self.fattr4_type != NF4REG:
            raise "write called on non file!"                              
        if count == 0:                                                     
            return 0
        fd = os.open(self.file, os.O_RDWR)                                 
        os.fsync(fd)                                                       
        os.close(fd)
        self.fattr4_time_metadata = converttime()                          
        return count  

class CallBackProxy(object):
    def cb_create(self, opcode, filename):
        if opcode == OP_CREATE_FILE:
            fd = os.open(filename, os.O_CREAT)
            os.close(fd)
        if opcode == OP_CREATE_DIR:
            os.mkdir(filename)
        return True

    def cb_remove(self, opcode, filename):
        if opcode == OP_REMOVE_FILE:
            os.remove(filename)
        if opcode == OP_REMOVE_DIR:
            shutil.rmtree(filename)
        return True

    def cb_write(self, filename, offset, length, wtype, payload):
        if wtype == COMPRESSED:
            data = zlib.decompress(payload)
            fd = os.open(filename, os.O_RDWR)
            size = libc.pwrite(fd, data, length, offset)
            os.close(fd)
            return size
        if wtype == DISCARD:
            fd = open(filename, "a+")
            fd.truncate(length)
            fd.close()
        if wtype == ZERO:
            stat_struct = os.stat(filename)
            old_size = stat_struct.st_size
            fd = os.open(filename, os.O_RDWR)
            size = length - old_size
            sz = libc.pwrite(fd, chr(0) * size, size, old_size)
            os.close(fd)
        return True

class ReplicaHandle(HardHandle, CallBackProxy):
    def __init__(self, filesystem, name, parent, file, raft = None):
        HardHandle.__init__(self, filesystem, name, parent, file)
        if parent:
            self.raft = parent.raft
        else:
            assert raft is not None
            self.raft = raft

    def set_fattr3_size(self, newsize):
        if self.fattr3_type == NF3REG and (newsize != self.fattr3_size or newsize == 0):
            nfsop = NFSOP()
            if newsize <= self.fattr3_size:
        	nfsop.opcode = OP_WRITE_DATA
	        nfsop.write.filename = self.file
	        nfsop.write.offset = 0
	        nfsop.write.length = newsize
	        nfsop.write.type = DISCARD
        	nfsop.write.payload = ''

                fd = open(self.file, "a+")
                fd.truncate(newsize)
                fd.close()
            else:
                # Pad with zeroes
        	nfsop.opcode = OP_WRITE_DATA
	        nfsop.write.filename = self.file
	        nfsop.write.offset = 0
	        nfsop.write.length = newsize
	        nfsop.write.type = ZERO
        	nfsop.write.payload = ''

                fd = os.open(self.file, os.O_RDWR)
                size = newsize - self.fattr3_size
                sz = libc.pwrite(fd, chr(0) * size, size, self.fattr3_size)
                os.close(fd)
            ret = self.raft.replicate(nfsop.SerializeToString())
            self.fattr3_size = newsize
            self.fattr3_time_modify = converttime()
        else:
            raise NFS3Error(NFS3ERR_INVAL)

    def create(self, name, type, attrs={}):
        """ Create a file of given type with given attrs, return attrs set

        type is a nfs3types.createtype3 instance
        """
        # Must make sure that if it fails, nothing is changed
        fullfile = os.path.join(self.file, name)
        if self.fattr3_type != NF3DIR:
            raise "create called on non-directory (%s)" % self.ref
        if os.path.exists(fullfile):
            raise "attempted to create already existing file."

        nfsop = NFSOP()

        if type.type == NF3DIR:
            nfsop.opcode = OP_CREATE_DIR
            nfsop.create.filename = fullfile

            os.mkdir(fullfile)

            ret = self.raft.replicate(nfsop.SerializeToString())
        else:
            nfsop.opcode = OP_CREATE_FILE
            nfsop.create.filename = fullfile

            fd = os.open(fullfile, os.O_CREAT)
            os.close(fd)

            ret = self.raft.replicate(nfsop.SerializeToString())
            
        fh = handle(None, name, self, fullfile)
        attrset = fh.set_attributes(attrs)
        self.dirent[name] = fh
        return attrset

    def write(self, offset, data):
        if self.fattr3_type != NF3REG:
            raise "write called on non file!"
        if len(data) == 0: 
            return 0

        self.fattr3_change += 1

        nfsop = NFSOP()

        nfsop.opcode = OP_WRITE_DATA
        nfsop.write.filename = self.file
        nfsop.write.offset = offset
        nfsop.write.length = len(data)
        nfsop.write.type = COMPRESSED
        nfsop.write.payload = zlib.compress(data)

        fd = os.open(self.file, os.O_RDWR)
        size = libc.pwrite(fd, data, len(data), offset)
        os.close(fd)

        ret = self.raft.replicate(nfsop.SerializeToString())

        self.fattr3_time_metadata = converttime()
        self.fattr3_size += size
        return size

    def remove(self, target):
        fullfile = os.path.join(self.file, target)
        if not os.path.exists(fullfile):
            raise "cannot find file."

        stat_struct = os.lstat(fullfile)

        nfsop = NFSOP()

        if S_ISDIR(stat_struct.st_mode):
            nfsop.opcode = OP_REMOVE_DIR
            nfsop.remove.filename = fullfile

            shutil.rmtree(fullfile)

            ret = self.raft.replicate(nfsop.SerializeToString())
        elif S_ISLNK(stat_struct.st_mode):
            os.unlink(fullfile)
        else:
            nfsop.opcode = OP_REMOVE_FILE
            nfsop.remove.filename = fullfile

            os.remove(fullfile)

            ret = self.raft.replicate(nfsop.SerializeToString())

        file = self.dirent[target]
        del self.dirent[target]
        file.destruct()

class DirList:
    def __init__(self):
        self.verifier = packnumber(int(time.time()))
        self.list = []
        self.__lastcookie = 2

    class DirEnt:
        def __init__(self, name, fh, cookie):
            self.name = name
            self.fh = fh
            self.cookie = cookie

    def __len__(self):
        return len(self.list)

    def __getitem__(self, name):
        """Allows  fh = self[name]"""
        for x in self.list:
            if x.name == name:
                return x.fh
        raise KeyError, "Invalid key %s" % name

    def __setitem__(self, name, fh):
        """Allows self[name] = fh"""
        # Remove if already in list
        for x in self.list:
            if x.name == name:
                del self.list[x]
        # Append to end of list
        self.list.append(self.DirEnt(name, fh, self.__nextcookie()))

    def __nextcookie(self):
        self.__lastcookie += 1
        return self.__lastcookie

    def __delitem__(self, name):
        """Allows del self[name]"""
        for x in self.list:
            if x.name == name:
                self.list.remove(x)
                return
        raise KeyError, "Invalid key %s" % name

    def getcookie(self, name):
        for x in self.list:
            if x.name == name:
                return x.cookie
        raise KeyError, "Invalid key %s" % name

    def readdir(self, cookie):
        """Returns DirEnt list containing all entries larger than cookie"""
        if cookie < 0 or cookie > self.__lastcookie:
            raise IndexError, "Invalid cookie %i" % cookie
        i = None
        for x in self.list:
            if x.cookie > cookie:
                i = self.list.index(x)
                break
        if i is None:
            return []
        else:
            logger.info(self.list[i:])
            return self.list[i:]

    def has_key(self, name):
        for x in self.list:
            if x.name == name:
                return True
        return False

    def keys(self):
        return [x.name for x in self.list]

    def values(self):
        return [x.fh for x in self.list]
