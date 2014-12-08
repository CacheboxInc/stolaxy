#!/usr/bin/env python
#
# nfs3server.py - NFS4 server in python
#
# Written by Martin Murray <mmurray@deepthought.org>
# and        Fred Isaman   <iisaman@citi.umich.edu>
# Copyright (C) 2001 University of Michigan, Center for 
#                    Information Technology Integration
#


try:
    import psyco
    psyco.full()
except:
    pass

import sys
if sys.hexversion < 0x02030000:
    print "Requires python 2.3 or higher"
    sys.exit(1)

import os
# Allow to be run stright from package root
if  __name__ == "__main__":
    if os.path.isfile(os.path.join(sys.path[0], 'lib', 'testmod.py')):
        sys.path.insert(1, os.path.join(sys.path[0], 'lib'))

import threading
import time, StringIO, random, traceback, codecs
import datetime
import getopt
import logging
from config import *
from xdrdef.nfs3_const import *
from xdrdef.nfs3_type import *
from xdrdef.nfs3_pack import *
from xdrdef.mnt3_const import *
from xdrdef.mnt3_type import *
from xdrdef.mnt3_pack import *
import rpc.rpc as rpc
from rpc.rpc import supported
from rpc.rpc import RPCVERSION, _readmask, _writemask, _bothmask, select 
from rpc.rpc_const import *
from rpc.rpc_type import *
import signal
from fs import *
from xdrlib import Error as XDRError

from args import args, parser

cwd = os.getcwd()

import struct
sys.path.append("%s/../../aio" % cwd)
import caio

unacceptable_names = [ "", ".", ".." ]
unacceptable_characters = [ "/", "~", "#", ]

logfile = "nfs_%s.log" % datetime.datetime.today().strftime('%Y%m%d')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('nfslog')
fh = logging.FileHandler(logfile)
fh.setFormatter(formatter)
logger.setLevel(logging.WARNING)
fh.setLevel(logging.WARNING)
logger.addHandler(fh)

NFS3AIO_ADDED = 200014
SUBMITTED = 6

def verify_name(name):
    """Check potential filename and return appropriate error code"""
    if len(name) == 0:
        raise NFS3Error(NFS3ERR_INVAL)
    if len(name) > NFS3_FHSIZE:
        raise NFS3Error(NFS3ERR_NAMETOOLONG)
    if name in unacceptable_names:
        raise NFS3Error(NFS3ERR_ACCES)
    for character in unacceptable_characters:
        if character in name:
            raise NFS3Error(NFS3ERR_ACCES)
    if not verify_utf8(name):
        raise NFS3Error(NFS3ERR_INVAL)

def verify_utf8(str):
    """Returns True if str is valid utf8, False otherwise"""
    try:
        ustr = codecs.utf_8_decode(str)
        return True
    except UnicodeError:
        return False
            
def access2string(access):
    ret = []
    if access & ACCESS3_READ:
        ret.append("ACCESS3_READ")
    if access & ACCESS3_LOOKUP:
        ret.append("ACCESS3_LOOKUP")
    if access & ACCESS3_MODIFY:
        ret.append("ACCESS3_MODIFY")
    if access & ACCESS3_EXTEND:
        ret.append("ACCESS3_EXTEND")
    if access & ACCESS3_DELETE:
        ret.append("ACCESS3_DELETE")
    if access & ACCESS3_EXECUTE:
        ret.append("ACCESS3_EXECUTE")
    return ' | '.join(ret)

def simple_error(error, *args):
    """Called from function O_<Name>, sets up and returns a simple error response"""
    name = sys._getframe(1).f_code.co_name # Name of calling function
    try:
        if name.startswith("op_"):
            command = name[3:]
            res = globals()[command.upper() + "3res"](error, *args);
            argop4 = nfs_resop4(globals()["OP_" + command.upper()])
            setattr(argop4, "op" + command, res)
            return (error, argop4)
    except KeyError:
        pass
    raise RuntimeError("Bad caller name %s" % name)

class MNT3Server(rpc.RPCServer):
    def __init__(self, rootfh, host, port):
        rpc.RPCServer.__init__(self, prog=MOUNT_PROGRAM, vers=MOUNT_V3,
                               host=host, port=port, name = "MNT")
        self.mnt3packer = MNT3Packer()
        self.mnt3unpacker = MNT3Unpacker('')
        self.fhcache = {}
        self.rootfh = rootfh

    def mount3proc_null(self, data, cred):
        if cred.flavor == rpc.RPCSEC_GSS:
            gss = self.security[cred.flavor]
            body = gss.read_cred(cred.body)
            if body.gss_proc:
                return gss.handle_proc(body, data)
        if data != '':
            logger.error("  ERROR - unexpected data")
            return rpc.GARBAGE_ARGS, ''
        else:
            return rpc.SUCCESS, ''

    def handle_request(self, data, cred, op):
        opname = mnt_opnum3.get(op, 'mountproc3_null').lower()
        if op == 0:
            return getattr(self, opname.lower())(data, cred)
        self.mnt3unpacker.reset(data)
        func = getattr(self, opname.lower(), None)
        if not func:
            return rpc.PROG_UNAVAIL, ''
        result = getattr(self, opname.lower())(data, cred)
        try:
            self.mnt3unpacker.done()
        except XDRError:
            logger.error(str(repr(self.mnt3unpacker.get_buffer())))
            raise
            return rpc.GARBAGE_ARGS, ''
        self.mnt3packer.reset()
        ret = str(result).split("(")[0]
        getattr(self.mnt3packer, "pack_%s" % ret)(result)
        return rpc.SUCCESS, self.mnt3packer.get_buffer()
 
    def mount3proc_mnt(self, data, cred):
        args = self.mnt3unpacker.unpack_dirpath()
        resok = mountres3_ok(fhandle=self.rootfh.file, auth_flavors=[AUTH_NONE, AUTH_SYS])
        result = mountres3(fhs_status=MNT3_OK, mountinfo = resok)
        return result

class NFS3Server(rpc.RPCServer):
    def __init__(self, rootfh, host, port, pubfh = None):
        rpc.RPCServer.__init__(self, prog=NFS_PROGRAM, vers=NFS_V3,
                               host=host, port=port, name = "NFS")
        self.nfs3packer = NFS3Packer()
        self.nfs3unpacker = NFS3Unpacker('')
        self.fhcache = {}
        self.rootfh = rootfh
        self.pubfh = pubfh
        self.verfnum = 0

    def nfs3proc_null(self, data, cred):
        if cred.flavor == rpc.RPCSEC_GSS:
            gss = self.security[cred.flavor]
            body = gss.read_cred(cred.body)
            if body.gss_proc:
                return gss.handle_proc(body, data)
        if data != '':
            logger.error("  ERROR - unexpected data")
            return rpc.GARBAGE_ARGS, ''
        else:
            return rpc.SUCCESS, ''

    def _get_fattr3_attributes(self, curr_fh):
        return fattr3(type = curr_fh.fattr3_type,
                      mode = curr_fh.fattr3_mode,
                      nlink = curr_fh.fattr3_numlinks,
                      uid = curr_fh.fattr3_uid,
                      gid = curr_fh.fattr3_gid,
                      size = curr_fh.fattr3_size,
                      used = curr_fh.fattr3_used,
                      rdev = curr_fh.fattr3_rdev,
                      fsid = curr_fh.fattr3_fsid,
                      fileid = curr_fh.fattr3_fileid,
                      atime = curr_fh.fattr3_atime,
                      mtime = curr_fh.fattr3_mtime,
                      ctime = curr_fh.fattr3_ctime
                     )

    def handle_request(self, data, cred, op):
        opname = nfs_opnum3.get(op, 'nfsproc3_null').lower()
        if op == 0:
            return getattr(self, opname.lower())(data, cred)
        self.nfs3unpacker.reset(data)
        func = getattr(self, opname.lower(), None)
        if not func:
            return rpc.PROG_UNAVAIL, ''
        result = getattr(self, opname.lower())(data, cred)
        try:
            self.nfs3unpacker.done()
        except XDRError:
            logger.error(str(repr(self.nfs3unpacker.get_buffer())))
            return rpc.GARBAGE_ARGS, ''
        if result is None:
            logger.error("NFS operation(%s) not supported" % opname)
            return rpc.GARBAGE_ARGS, ''
        self.nfs3packer.reset()
        ret = str(result).split("(")[0]
        getattr(self.nfs3packer, "pack_%s" % ret)(result)
        return rpc.SUCCESS, self.nfs3packer.get_buffer()
    
    def nfs3proc_getattr(self, data, cred):
        args = self.nfs3unpacker.unpack_GETATTR3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.object.data))
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_BADHANDLE)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            status = NFS3_OK
        except NFS3Error as e:
            logger.error("nfs3proc_getattr : %s" % e)
            attributes = {}
            status = e.code
        resok = GETATTR3resok(obj_attributes=attributes)
        result = GETATTR3res(status=status, resok=resok)
        return result

    def nfs3proc_setattr(self, data, cred):
        args = self.nfs3unpacker.unpack_SETATTR3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.object.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)

            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            attrs = {}
            if args.guard.check == TRUE and \
                (args.guard.obj_ctime.seconds != self.curr_fh.fattr3_ctime.seconds or \
                args.guard.obj_ctime.nanoseconds != self.curr_fh.fattr3_ctime.nanoseconds):
                raise NFS3Error(NFS3ERR_NOT_SYNC)

            if args.new_attributes.mode.set_it:
                attrs['fattr3_mode'] = args.new_attributes.mode.mode
            if args.new_attributes.gid.set_it:
                attrs['fattr3_gid'] = args.new_attributes.gid.gid
            if args.new_attributes.uid.set_it:
                attrs['fattr3_uid'] = args.new_attributes.uid.uid
            if args.new_attributes.size.set_it:
                attrs['fattr3_size'] = args.new_attributes.size.size
            if args.new_attributes.atime.set_it == SET_TO_SERVER_TIME:
                attrs['fattr3_atime'] = converttime()
            if args.new_attributes.mtime.set_it == SET_TO_SERVER_TIME:
                attrs['fattr3_mtime'] = converttime()
            if args.new_attributes.atime.set_it == SET_TO_CLIENT_TIME:
                attrs['fattr3_size'] = args.new_attributes.atime.atime
            if args.new_attributes.mtime.set_it == SET_TO_CLIENT_TIME:
                attrs['fattr3_size'] = args.new_attributes.mtime.mtime

            self.curr_fh.set_fattr3_attributes(attrs)
         
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = SETATTR3resok(obj_wcc=obj_wcc)
        except NFS3Error as e:
            logger.error("nfs3proc_setattr : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = SETATTR3resfail(obj_wcc=obj_wcc)
        result = SETATTR3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_lookup(self, data, cred):
        args = self.nfs3unpacker.unpack_LOOKUP3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.what.dir.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() == NF3LNK:
                raise NFS3Error(NFS3ERR_MLINK)
            if self.curr_fh.get_type() != NF3DIR:
                raise NFS3Error(NFS3ERR_NOTDIR)
            verify_name(args.what.name)

            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_dir_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            file_obj = self.curr_fh.lookup(str(args.what.name))
            if file_obj:
                attributes = self._get_fattr3_attributes(file_obj)
                post_obj_file_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
                resok = LOOKUP3resok(object=nfs_fh3(data=file_obj.file), \
                                 obj_attributes=post_obj_file_attr, dir_attributes=post_dir_obj_attr)
            else:
                raise NFS3Error(NFS3ERR_NOENT)
        except NFS3Error as e:
            logger.error("nfs3proc_lookup : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_dir_obj_attr
            except:
                post_dir_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = LOOKUP3resfail(dir_attributes=post_dir_obj_attr)
        result = LOOKUP3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_access(self, data, cred):
        args = self.nfs3unpacker.unpack_ACCESS3args()
        try:
            status = NFS3_OK
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            if not args.access & self.curr_fh.supported_access():
                raise NFS3Error(NFS3ERR_ACCES)
            resok = ACCESS3resok(obj_attributes=post_obj_attr, access=args.access)
        except NFS3Error as e:
            logger.error("nfs3proc_access : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_obj_attr
            except:
                post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = ACCESS3resfail(obj_attributes=post_obj_attr)
        result = ACCESS3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_readlink(self, data, cred):
        args = self.nfs3unpacker.unpack_READLINK3args()
        try:
            status = NFS3_OK
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() != NF3LNK:
                raise NFS3Error(NFS3ERR_INVAL)
            link = self.curr_fh.read_link()
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = READLINK3resok(symlink_attributes=post_obj_attr, data=link)
        except NFS3Error as e:
            logger.error("nfs3proc_readlink : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_obj_attr
            except:
                post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = READLINK3resfail(symlink_attributes=post_obj_attr)
        result = READLINK3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_read(self, data, cred):
        args = self.nfs3unpacker.unpack_READ3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.file.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() == NF3DIR:
                raise NFS3Error(NFS3ERR_ISDIR)
            if self.curr_fh.get_type() != NF3REG:
                raise NFS3Error(NFS3ERR_INVAL)
            buf = self.curr_fh.read(args.offset, args.count)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            eof = 1
            if (len(buf) < args.count):
                eof = 0
            resok = READ3resok(file_attributes=post_obj_attr, count=len(buf), eof=eof, data=buf)
        except NFS3Error as e:
            logger.error("nfs3proc_read : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_obj_attr
            except:
                post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = READ3resfail(file_attributes=post_obj_attr)
        result = READ3res(status=status, resok=resok, resfail=resfail)
        return result
 
    def nfs3proc_write(self, data, cred):
        args = self.nfs3unpacker.unpack_WRITE3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.file.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() == NF3DIR:
                raise NFS3Error(NFS3ERR_ISDIR)
            if self.curr_fh.get_type() != NF3REG:
                raise NFS3Error(NFS3ERR_INVAL)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            size = self.curr_fh.write(args.offset, args.data, count=args.count,stable=args.stable)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = WRITE3resok(file_wcc=obj_wcc, count=size, committed=args.stable, verf=self.curr_fh.write_verifier)
        except NFS3Error as e:
            logger.error("nfs3proc_write : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = WRITE3resfail(file_wcc=obj_wcc)
        result = WRITE3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_create(self, data, cred):
        args = self.nfs3unpacker.unpack_CREATE3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.where.dir.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            verify_name(args.where.name)
            if not self.curr_fh.get_type() == NF3DIR:
                raise NFS3Error(NFS3ERR_NOTDIR)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            attr = {}
            if args.how.mode == EXCLUSIVE:
                verf = args.how.verf
            else:
                attr = args.how.obj_attributes
            self.curr_fh.create(args.where.name, mode=args.how.mode, attrs=attr)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            self.curr_fh = self.curr_fh.lookup(str(args.where.name))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_SERVERFAULT)
            pfh3_obj = post_op_fh3(handle_follows=TRUE, handle=nfs_fh3(data=self.curr_fh.file))
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_file_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = CREATE3resok(obj=pfh3_obj, obj_attributes=post_obj_file_attr, dir_wcc=obj_wcc)
        except NFS3Error as e:
            logger.error("nfs3proc_create : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = CREATE3resfail(dir_wcc=obj_wcc)
        result = CREATE3res(status=status, resok=resok, resfail=resfail) 
        return result

    def nfs3proc_mkdir(self, data, cred):
        args = self.nfs3unpacker.unpack_MKDIR3args()
        try:
            status = NFS3_OK
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            verify_name(args.where.name)
            if not self.curr_fh.get_type() == NF3DIR:
                raise NFS3Error(NFS3ERR_NOTDIR)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            attr = args.attributes
            self.curr_fh.mkdir(args.where.name, attrs=attr)

            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            self.curr_fh = self.curr_fh.lookup(str(args.where.name))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_SERVERFAULT)
            pfh3_obj = post_op_fh3(handle_follows=TRUE, handle=nfs_fh3(data=self.curr_fh.file))
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_file_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = MKDIR3resok(obj=pfh3_obj, obj_attributes=post_obj_file_attr, dir_wcc=obj_wcc)
        except NFS3Error as e:
            logger.error("nfs3proc_mkdir : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = MKDIR3resfail(dir_wcc=obj_wcc)
        result = MKDIR3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_symlink(self, data, cred):
        return None # NFS3Error(NFS3ERR_NOTSUPP)

    def nfs3proc_mknod(self, data, cred):
        return None # NFS3Error(NFS3ERR_NOTSUPP)

    def nfs3proc_remove(self, data, cred):
        args = self.nfs3unpacker.unpack_REMOVE3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.object.data))
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() != NF3DIR:
                raise NFS3Error(NFS3ERR_NOTDIR)
            verify_name(args.name)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            self.curr_fh.remove(args.name)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = REMOVE3resok(dir_wcc=obj_wcc)
        except NFS3Error as e:
            logger.error("nfs3proc_remove : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = REMOVE3resfail(dir_wcc=obj_wcc)
        result = REMOVE3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_rmdir(self, data, cred):
        args = self.nfs3unpacker.unpack_RMDIR3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.dir.data))
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() != NF3DIR:
                raise NFS3Error(NFS3ERR_NOTDIR)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            self.curr_fh.rmdir(args.name)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = RMDIR3resok(dir_wcc=obj_wcc)
        except NFS3Error as e:
            logger.error("nfs3proc_rmdir : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = RMDIR3resfail(dir_wcc=obj_wcc)
        result = RMDIR3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_rename(self, data, cred):
        args = self.nfs3unpacker.unpack_RENAME3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.fromfile.dir.data))
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            verify_name(args.tofile.name)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_from_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            self.curr_from_fh = self.curr_fh
            self.curr_fh = self.rootfh.lookup(str(args.tofile.dir.data))
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_to_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            self.curr_fh.rename(self.curr_from_fh, args.fromfile.name, args.tofile.name)
            self.curr_fh = self.rootfh.lookup(str(args.fromfile.dir.data))
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_from_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)

            self.curr_from_fh = self.curr_fh
            self.curr_fh = self.rootfh.lookup(str(args.tofile.dir.data))
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_to_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            from_obj_wcc = wcc_data(before=pre_from_obj_attr, after=post_from_obj_attr)
            to_obj_wcc = wcc_data(before=pre_to_obj_attr, after=post_to_obj_attr)

            resok = RENAME3resok(fromdir_wcc=from_obj_wcc, todir_wcc=to_obj_wcc)
        except NFS3Error as e:
            logger.error("nfs3proc_rename : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_from_obj_attr
            except:
                pre_from_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            try:
                pre_to_obj_attr
            except:
                pre_to_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_from_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_to_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            from_obj_wcc = wcc_data(before=pre_from_obj_attr, after=post_from_obj_attr)
            to_obj_wcc = wcc_data(before=pre_to_obj_attr, after=post_to_obj_attr)
            resok = None
        resfail = RENAME3resfail(fromdir_wcc=from_obj_wcc, todir_wcc=to_obj_wcc)
        result = RENAME3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_link(self, data, cred):
        return None # NFS3Error(NFS3ERR_NOTSUPP)
        
    def nfs3proc_readdir(self, data, cred):
        args = self.nfs3unpacker.unpack_READDIR3args()
        cookie = args.cookie
        cookieverf = args.cookieverf
        count = args.count
        try:
            status = NFS3_OK
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            verifier = self.curr_fh.getdirverf()
            if cookie != 0:
                if cookieverf != verifier:
                    raise NFS3Error(NFS3ERR_BAD_COOKIE)

            try:
                dirlist = self.curr_fh.read_dir(cookie)
            except IndexError:
                raise NFS3Error(NFS3ERR_BAD_COOKIE)
            entries = []
            bytecnt = 0
            packer = NFS3Packer()
            for entry in dirlist:
                attributes = self._get_fattr3_attributes(entry)
                attrvals = post_op_attr(attributes_follow=TRUE, attributes=attributes)
                entry.attr = attrvals
                # Compute size of XDR encoding
                e3 = entry3(fileid=entry.fattr3_fileid, name=entry.name, cookie=entry.cookie, nextentry=[])
                packer.reset()
                packer.pack_entry3(e3)
                # Make sure returned value not too big
                bytecnt += len(packer.get_buffer())
                if bytecnt > count - 16:
                    break
                # Add file to returned entries
                entries.insert(0, entry)
            if (not entries) and dirlist:
                raise NFS3Error(NFS3ERR_TOOSMALL)
            # Encode entries as linked list
            e3 = []
            for entry in entries:
                e3 = [entry3(fileid=entry.fattr3_fileid, name=entry.name, cookie=entry.cookie, nextentry=e3)]
            if len(entries) < len(dirlist):
                d3 = dirlist3(entries=e3, eof=0)
            else:
                d3 = dirlist3(entries=e3, eof=1)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = READDIR3resok(dir_attributes=post_obj_attr, cookieverf=verifier, reply=d3)
        except NFS3Error as e:
            logger.error("nfs3proc_readdir : %s" % e)
            status = e.code
            attributes = {}
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = READDIR3resfail(dir_attributes=post_obj_attr)
        result = READDIR3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_readdirplus(self, data, cred):
        args = self.nfs3unpacker.unpack_READDIRPLUS3args()
        cookie = args.cookie
        cookieverf = args.cookieverf
        dircount = args.dircount
        maxcount = args.maxcount
        try:
            status = NFS3_OK
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            verifier = self.curr_fh.getdirverf()
            if cookie != 0:
                if cookieverf != verifier:
                    raise NFS3Error(NFS3ERR_BAD_COOKIE)
            try:
                dirlist = self.curr_fh.read_dir(cookie)
            except IndexError:
                raise NFS3Error(NFS3ERR_BAD_COOKIE)
            entries = []
            bytecnt = 0
            packer = NFS3Packer()
            for entry in dirlist:
                # Compute size of XDR encoding
                attributes = self._get_fattr3_attributes(entry)
                name_attributes = post_op_attr(attributes_follow=TRUE, attributes=attributes)
                name_handle = post_op_fh3(handle_follows=TRUE, handle=nfs_fh3(data=entry.file))
                entry.attr = name_attributes
                entry.name_handle = name_handle
                e3 = entryplus3(fileid=entry.fattr3_fileid, name=entry.name, cookie=entry.cookie, 
                                name_attributes=name_attributes, name_handle=name_handle, nextentry=[])
                packer.reset()
                packer.pack_entry3(e3)
                # Make sure returned value not too big
                bytecnt += len(packer.get_buffer())
                if bytecnt > maxcount - 16:
                    break
                # Add file to returned entries
                entries.insert(0, entry)
            if (not entries) and dirlist:
                raise NFS3Error(NF3ERR_TOOSMALL)
            # Encode entries as linked list
            e3 = []
            for entry in entries:
                e3 = [entryplus3(fileid=entry.fattr3_fileid, name=entry.name, cookie=entry.cookie,
                                name_attributes=entry.attr, name_handle=entry.name_handle, nextentry=e3)]
            if len(entries) < len(dirlist):
                d3 = dirlistplus3(entries=e3, eof=0)
            else:
                d3 = dirlistplus3(entries=e3, eof=1)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = READDIRPLUS3resok(dir_attributes=post_obj_attr, cookieverf=verifier, reply=d3)
        except NFS3Error as e:
            logger.error("nfs3proc_readdirplus : %s" % e)
            status = e.code
            attributes = {}
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = READDIRPLUS3resfail(dir_attributes=post_obj_attr)
        result = READDIRPLUS3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_fsstat(self, data, cred):
        return None # NFS3Error(NFS3ERR_NOTSUPP)

    def nfs3proc_fsinfo(self, data, cred):
        args = self.nfs3unpacker.unpack_FSINFOargs()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.fsroot.data))
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = FSINFO3resok(obj_attributes=post_obj_attr,
                                 rtmax=self.curr_fh.fattr3_rtmax,
                                 rtpref=self.curr_fh.fattr3_rtpref,
                                 rtmult=self.curr_fh.fattr3_rtmult,
                                 wtmax=self.curr_fh.fattr3_wtmax,
                                 wtpref=self.curr_fh.fattr3_wtpref,
                                 wtmult=self.curr_fh.fattr3_wtmult,
                                 dtpref=self.curr_fh.fattr3_dtpref,
                                 maxfilesize=self.curr_fh.fattr3_maxfilesize, 
                                 time_delta=self.curr_fh.fattr3_time_delta,
                                 properties=self.curr_fh.fattr3_properties
                                )
        except NFS3Error as e:
            logger.error("nfs3proc_fsinfo : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_obj_attr
            except:
                post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = FSINFO3resfail(obj_attributes=post_obj_attr)
        result = FSINFO3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_pathconf(self, data, cred):
        args = self.nfs3unpacker.unpack_PATHCONF3args()
        try:
            status = NFS3_OK
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = PATHCONF3resok(obj_attributes=post_obj_attr,
                                   linkmax=0, 
                                   name_max=NFS3_FHSIZE,
                                   no_trunc=TRUE,
                                   chown_restricted=TRUE,
                                   case_insensitive=FALSE,
                                   case_preserving=TRUE
                                  )
        except NFS3Error as e:
            logger.error("nfs3proc_pathconf : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_obj_attr
            except:
                post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = PATHCONF3resfail(obj_attributes=post_obj_attr)
        result = PATHCONF3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_commit(self, data, cred):
        args = self.nfs3unpacker.unpack_COMMIT3args()
        try:
            status = NFS3_OK
            if self.curr_fh is None:
                raise NFS3Error(NFS3ERR_NOENT)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            self.curr_fh.commit(args.offset, args.count)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = COMMIT3resok(file_wcc=obj_wcc, verf=self.curr_fh.write_verifier)
        except NFS3Error as e:
            logger.error("nfs3proc_commit : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = COMMIT3resfail(file_wcc=obj_wcc)
        result = COMMIT3res(status=status, resok=resok, resfail=resfail)
        return result

class NFS3AIOServer(NFS3Server):

    def __init__(self, rootfh, host, port, pubfh = None):
        NFS3Server.__init__(self, rootfh, port=port, host=host, pubfh=rootfh)
        self.QUEUE_DEPTH = 32
        self.ios = 0
        self.aio = caio.AIO()
        self.aio.io_setup(self.QUEUE_DEPTH)
        self.aio.io_reset()
        self.now = datetime.datetime.now()
        self.xid_res = {}
        self.fds = {'DIRECT': {}, 'INDIRECT': {}}

    def package_response(self, xid, cred, result):
        flavor = cred.flavor
        rreply = None
        reply_stat = MSG_ACCEPTED
        self.nfs3packer.reset()
        ret = str(result).split("(")[0]
        getattr(self.nfs3packer, "pack_%s" % ret)(result)
        a_stat, proc_response = rpc.SUCCESS, self.nfs3packer.get_buffer()
        proc_response = self.security[flavor].secure_data(proc_response, cred)
        verf = self.security[flavor].make_reply_verf(cred, a_stat)
        areply = accepted_reply(verf, rpc_reply_data(a_stat, ''))
        body = reply_body(reply_stat, areply, rreply)
        msg = rpc_msg(xid, rpc_msg_body(REPLY, rbody=body))
        self.rpcpacker.reset()
        self.rpcpacker.pack_rpc_msg(msg)
        return self.rpcpacker.get_buffer() + proc_response

    def process_reads(self, fh, buf, count):
        attributes = self._get_fattr3_attributes(fh)
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        eof = 1
        if (len(buf) < count):
            eof = 0
        resok = READ3resok(file_attributes=post_obj_attr, count=len(buf), eof=eof, data=buf)
        resfail = READ3resfail(file_attributes=post_obj_attr)
        result = READ3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def process_writes(self, fh, pre_obj_attr, size, stable):
        attributes = self._get_fattr3_attributes(fh)
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resok = WRITE3resok(file_wcc=obj_wcc, count=size, committed=stable, verf=fh.write_verifier)
        post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resfail = WRITE3resfail(file_wcc=obj_wcc)
        result = WRITE3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def process_aios(self):
        self.aio.io_submit()
        ret = 0
        if not self.recordbufs.has_key(self.fd):
            return
        while True:
            r = self.aio.io_getevents()
            ret += r['total']
            for xid, res, buf in r['reads']:
                #print "*** READS done %s ***" % (xid)
                cred = self.xid_res[xid]['cred']
                fh = self.xid_res[xid]['fh']
                count = self.xid_res[xid]['count']
                self.xid_res[xid]['ref'] -= 1
                if self.xid_res[xid]['ref'] == 0:
                    del self.xid_res[xid]
                result = self.process_reads(fh, buf, count)
                reply = self.package_response(xid, cred, result)
                self.recordbufs[self.fd].append(reply)
                self.p.register(self.fd, _bothmask)
            for xid, res in r['writes']:
                #print "*** WRITES done %s %s ***" % (xid, res)
                cred = self.xid_res[xid]['cred']
                fh = self.xid_res[xid]['fh']
                pre_obj_attr = self.xid_res[xid]['pre_obj_attr']
                stable = self.xid_res[xid]['stable']
                self.xid_res[xid]['ref'] -= 1
                if self.xid_res[xid]['ref'] == 0:
                    del self.xid_res[xid]
                result = self.process_writes(fh, pre_obj_attr, res, stable)
                reply = self.package_response(xid, cred, result)
                self.recordbufs[self.fd].append(reply)
                self.p.register(self.fd, _bothmask)
            if ret == self.ios:
                break
        for fd in self.fds['DIRECT'].values():
            os.close(fd)
        for fd in self.fds['INDIRECT'].values():
            os.close(fd)
        self.fds = {'DIRECT': {}, 'INDIRECT': {}}
        self.ios = 0
        self.aio.io_reset()
        self.now = datetime.datetime.now()
        self.event_write(self.fd)

    def run(self, debug=0):
        while 1:
            logger.info("%s: Calling poll %s" % (self.name, self.recv_size))
            res = self.p.poll(100)
            logger.info("%s: %s" % (self.name, res))
            if self.ios == self.QUEUE_DEPTH or \
                ((datetime.datetime.now() - self.now).microseconds > 10000 and self.ios > 0):
                self.process_aios()
            for fd, event in res:
                self.fd = fd
                logger.info( "%s: Handling fd=%i, event=%x" % \
                          (self.name, fd, event))
                if event & select.POLLHUP:
                    self.event_hup(fd)
                elif event & select.POLLNVAL:
                    if debug: logger.info("%s: POLLNVAL for fd=%i" % (self.name, fd))
                    self.p.unregister(fd)
                elif event & ~(select.POLLIN | select.POLLOUT):
                    logger.info("%s: ERROR: event %i for fd %i" % \
                          (self.name, event, fd))
                    self.event_error(fd)
                else:
                    if event & select.POLLOUT:
                        self.event_write(fd)
                    # This must be last since may call close
                    if event & select.POLLIN:
                        if fd == self.s.fileno():
                            self.event_connect(fd)
                        else:
                            data = self.sockets[fd].recv(self.recv_size)
                            if data:
                                self.event_read(fd, data)
                            else:
                                self.event_close(fd)

    def event_read(self, fd, data, debug=0):
        """Reads incoming record marked packets

        Also responds to command codes sent as encoded integers
        """
        if debug: logger.info("SERVER: In read event for %i" % fd)
        self.readbufs[fd] += data
        loop = True
        while loop:
            loop = False
            str = self.readbufs[fd]
            if len(str) >= 4:
                packetlen = struct.unpack('>L', str[0:4])[0]
                last = 0x80000000L & packetlen
                packetlen &= 0x7fffffffL
                if len(str) >= 4 + packetlen:
                    self.packetbufs[fd].append(str[4:4 + packetlen])
                    self.readbufs[fd] = str[4 + packetlen:]
                    if self.readbufs[fd]:
                        loop = True # We've received data past last 
                    if last:
                        if debug: logger.info("SERVER: Received record from %i" % fd)
                        recv_data = ''.join(self.packetbufs[fd])
                        self.packetbufs[fd] = []
                        if len(recv_data) == 4:
                            reply = self.event_command(fd, struct.unpack('>L', recv_data)[0])
                        else:
                            # All handle_* functions are called in compute_reply
                            reply = self.compute_reply(recv_data)
                        if reply is not None:
                            self.recordbufs[fd].append(reply)
                            self.p.register(fd, _bothmask)
            if self.ios == self.QUEUE_DEPTH or \
                ((datetime.datetime.now() - self.now).microseconds > 10000 and self.ios > 0):
                self.process_aios()
                        
    def compute_reply(self, recv_data):
        # Decode RPC specific info
        self.rpcunpacker.reset(recv_data)
        try:
            recv_msg = self.rpcunpacker.unpack_rpc_msg()
        except xdrlib.Error, e:
            print "XDRError", e
            return
        if recv_msg.body.mtype != CALL:
            print "Received a REPLY, expected a CALL"
            return
        # Check for reasons to deny the call
        call = recv_msg.body.cbody
        cred = call.cred
        flavor = cred.flavor
        #print call
        reply_stat = MSG_ACCEPTED
        areply = rreply = None
        proc_response = ''
        if call.rpcvers != RPCVERSION:
            rreply = rejected_reply(RPC_MISMATCH,
                                    rpc_mismatch_info(RPCVERSION, RPCVERSION))
            reply_stat = MSG_DENIED
        elif flavor not in self.security: # STUB
            # Auth checking
            rreply = rejected_reply(AUTH_ERROR, astat=AUTH_FAILED)
            reply_stat = MSG_DENIED
        # At this point recv_msg has been accepted
        # Check for reasons to fail before calling handle_*
        meth_data = recv_data[self.rpcunpacker.get_position():]
        meth_data = self.security[flavor].unsecure_data(meth_data, cred)
        if rreply:
            pass
        elif self.prog != call.prog:
            verf = self.security[flavor].make_reply_verf(cred, PROG_UNAVAIL)
            areply = accepted_reply(verf, rpc_reply_data(PROG_UNAVAIL))
        elif self.vers != call.vers:
            verf = self.security[flavor].make_reply_verf(cred, PROG_MISMATCH)
            mismatch = rpc_mismatch_info(self.vers, self.vers)
            areply = accepted_reply(verf,
                                    rpc_reply_data(PROG_MISMATCH,
                                                   mismatch_info=mismatch))
        elif not hasattr(self, "handle_request"):
            verf = self.security[flavor].make_reply_verf(cred, PROG_UNAVAIL)
            areply = accepted_reply(verf, rpc_reply_data(PROC_UNAVAIL))
        else:
            method = getattr(self, "handle_request")
            a_stat, proc_response = method(meth_data, cred, call.proc, recv_msg.xid)
            if a_stat == PROG_UNAVAIL:
                verf = self.security[flavor].make_reply_verf(cred, PROG_UNAVAIL)
                areply = accepted_reply(verf, rpc_reply_data(PROC_UNAVAIL))
            else:
                verf = self.security[flavor].make_reply_verf(cred, a_stat)
                if a_stat == SUBMITTED:
                    return None
                if a_stat == SUCCESS:
                    proc_response = self.security[flavor].secure_data(proc_response, cred)
                areply = accepted_reply(verf, rpc_reply_data(a_stat, ''))
        # Build reply
        body = reply_body(reply_stat, areply, rreply)
        msg = rpc_msg(recv_msg.xid, rpc_msg_body(REPLY, rbody=body))
        self.rpcpacker.reset()
        self.rpcpacker.pack_rpc_msg(msg)
        return self.rpcpacker.get_buffer() + proc_response

    def handle_request(self, data, cred, op, xid):
        opname = nfs_opnum3.get(op, 'nfsproc3_null').lower()
        if op == 0:
            return getattr(self, opname.lower())(data, cred)

        if not self.xid_res.has_key(xid):
            self.xid_res[xid] = {'ref' : 0, 'cred': cred}
        self.xid_res[xid]['ref'] += 1

        self.nfs3unpacker.reset(data)
        func = getattr(self, opname.lower(), None)
        if not func:
            return rpc.PROG_UNAVAIL, ''
        if opname.lower() in ['nfs3proc_read', 'nfs3proc_write']:
            result = getattr(self, opname.lower())(data, cred, xid)
        else:
            result = getattr(self, opname.lower())(data, cred)
        try:
            self.nfs3unpacker.done()
        except XDRError:
            logger.error(str(repr(self.nfs3unpacker.get_buffer())))
            return rpc.GARBAGE_ARGS, ''
        if result is None:
            logger.error("NFS operation(%s) not supported" % opname)
            return rpc.GARBAGE_ARGS, ''
        if result == NFS3AIO_ADDED:
            return SUBMITTED, ''
        self.xid_res[xid]['ref'] -= 1
        if self.xid_res[xid]['ref'] == 0:
            del self.xid_res[xid]
        self.nfs3packer.reset()
        ret = str(result).split("(")[0]
        getattr(self.nfs3packer, "pack_%s" % ret)(result)
        return rpc.SUCCESS, self.nfs3packer.get_buffer()

    def nfs3proc_read(self, data, cred, xid):
        args = self.nfs3unpacker.unpack_READ3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.file.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() == NF3DIR:
                raise NFS3Error(NFS3ERR_ISDIR)
            if self.curr_fh.get_type() != NF3REG:
                raise NFS3Error(NFS3ERR_INVAL)
            buf = self.curr_fh.read(xid, self.aio, self.fds, args.offset, args.count)
            self.xid_res[xid]['fh'] = self.curr_fh
            self.xid_res[xid]['count'] = args.count
            self.ios += 1
            return NFS3AIO_ADDED
        except NFS3Error as e:
            logger.error("nfs3proc_read : %s" % e)
            status = e.code
            attributes = {}
            try:
                post_obj_attr
            except:
                post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            resok = None
        resfail = READ3resfail(file_attributes=post_obj_attr)
        result = READ3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_write(self, data, cred, xid):
        args = self.nfs3unpacker.unpack_WRITE3args()
        try:
            status = NFS3_OK
            self.curr_fh = self.rootfh.lookup(str(args.file.data))
            if not self.curr_fh:
                raise NFS3Error(NFS3ERR_NOENT)
            if self.curr_fh.get_type() == NF3DIR:
                raise NFS3Error(NFS3ERR_ISDIR)
            if self.curr_fh.get_type() != NF3REG:
                raise NFS3Error(NFS3ERR_INVAL)
            attributes = self._get_fattr3_attributes(self.curr_fh)
            pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            size = self.curr_fh.write(xid, self.aio, self.fds, args.offset, args.data, args.count, args.stable)
            self.xid_res[xid]['fh'] = self.curr_fh
            self.xid_res[xid]['pre_obj_attr'] = pre_obj_attr
            self.xid_res[xid]['stable'] = args.stable
            self.ios += 1
            return NFS3AIO_ADDED
        except NFS3Error as e:
            logger.error("nfs3proc_write : %s" % e)
            status = e.code
            attributes = {}
            try:
                pre_obj_attr
            except:
                pre_obj_attr = pre_op_attr(attributes_follow=FALSE, attributes=attributes)
            post_obj_attr = post_op_attr(attributes_follow=FALSE, attributes=attributes)
            obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
            resok = None
        resfail = WRITE3resfail(file_wcc=obj_wcc)
        result = WRITE3res(status=status, resok=resok, resfail=resfail)
        return result

def startnfs3server(rootfh, port=2049, host='', pubfh=None, raft = None):
    server = NFS3Server(rootfh, port=port, host=host, pubfh=directory)
    #server = NFS3AIOServer(rootfh, port=port, host=host, pubfh=directory)
    try:
        import portmap as portmap
        if not portmap.set(NFS_PROGRAM, NFS_V3, 6, port):
            raise
        server.register()
    except Exception as e:
        logger.warn("!! unable to register with portmap")
        pass
    logger.debug("Python NFSv4 Server, (c) CITI, Regents of the University of Michigan")
    logger.debug("Starting Server, root handle: %s" % directory)

    server.run()
    try:
        server.unregister()
    except:
        pass

def mnt3server(rootfh, port=32767, host=''):
    server = MNT3Server(rootfh, port=port, host=host)
    try:
        import portmap as portmap
        if not portmap.set(MOUNT_PROGRAM, MOUNT_V3, 6, port):
            raise
        server.register()
    except Exception as e:
        logger.warn("!! unable to register with portmap")
        pass
    logger.debug("Python NFSv3 Server, (c) CITI, Regents of the University of Michigan")
    logger.debug("Starting Server, root handle: %s" % directory)

    server.run()
    try:
        server.unregister()
    except:
        pass

def startup(host, port, directory, raft = None):
    if htype == 'HARD_HANDLE':
        rootfh = HardHandle(None, "/", None, directory, 43567)
    elif htype == 'AIO_HANDLE':
        rootfh = AIOHandle(None, "/", None, directory, 43567)
    elif htype == 'NULL_HANDLE':
        rootfh = NullHandle(None, "/", None, directory, 43567)
    elif htype == 'REPLICA_HANDLE':
        rootfh = ReplicaHandle(None, "/", None, directory, raft, 43567)
    else:
        assert 0, "unknown htype"

    nfs = threading.Thread(
           target = startnfs3server,
           kwargs = {
                     'rootfh': rootfh,
                     'port': port,
                     'host': host,
                     'raft': raft
                     }
    )
    nfs.start()

    mnt = threading.Thread(
           target = mnt3server,
           kwargs = {
                     'rootfh': rootfh,
                     'port': 32767,
                     'host': host
                    }
    )
    mnt.start()

    nfs.join()
    mnt.join()

if __name__ == "__main__":
    port = 2049
    server = ''
    debug = False
    directory = "/tmp"

    debug = args.debug
    directory = args.export

    if debug:
        logger.setLevel(logging.INFO)
        fh.setLevel(logging.INFO)

    startup(server, port, directory)
