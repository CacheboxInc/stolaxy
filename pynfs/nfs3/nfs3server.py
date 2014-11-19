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
from rpc.rpc_const import *
import signal
from fs import *
from xdrlib import Error as XDRError

from args import args, parser

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

def verify_name(name):
    """Check potential filename and return appropriate error code"""
    if len(name) == 0:
        return NFS3ERR_INVAL
    if len(name) > NFS3_FHSIZE:
        return NFS3ERR_NAMETOOLONG
    if name in unacceptable_names:
        return NFS3ERR_ACCES
    for character in unacceptable_characters:
        if character in name:
            return NFS3ERR_ACCES
    if not verify_utf8(name):
        return NFS3ERR_INVAL
    return NFS3_OK

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
        logger.info("******** TCP RPC NULL CALL ********")
        logger.info("  flavor = %i" % cred.flavor)
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
        logger.info("******** TCP RPC NULL CALL ********")
        logger.info("  flavor = %i" % cred.flavor)
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

    def _get_fattr3_attributes(self):
        return fattr3(type=self.curr_fh.fattr3_type,
                            mode=self.curr_fh.fattr3_mode,
                            nlink=self.curr_fh.fattr3_numlinks,
                            uid=self.curr_fh.fattr3_uid,
                            gid=self.curr_fh.fattr3_gid,
                            size=self.curr_fh.fattr3_size,
                            used=self.curr_fh.fattr3_used,
                            rdev=self.curr_fh.fattr3_rdev,
                            fsid=self.curr_fh.fattr3_fsid,
                            fileid=self.curr_fh.fattr3_fileid,
                            atime=self.curr_fh.fattr3_atime,
                            mtime=self.curr_fh.fattr3_mtime,
                            ctime=self.curr_fh.fattr3_ctime
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
        self.curr_fh = self.rootfh.lookup(str(args.object.data))
        status = NFS3_OK
        attributes = self._get_fattr3_attributes()
        resok = GETATTR3resok(obj_attributes=attributes)
        result = GETATTR3res(status=NFS3_OK, resok=resok)
        return result

    def nfs3proc_setattr(self, data, cred):
        args = self.nfs3unpacker.unpack_SETATTR3args()
        self.curr_fh = self.rootfh.lookup(str(args.object.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        status = NFS3_OK
        attrs = {}
        if args.guard.check == TRUE and \
            (args.guard.obj_ctime.seconds != self.curr_fh.fattr3_ctime.seconds or \
            args.guard.obj_ctime.nanoseconds != self.curr_fh.fattr3_ctime.nanoseconds):
            status = NFS3ERR_BADHANDLE

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
         
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resok = SETATTR3resok(obj_wcc=obj_wcc)
        resfail = SETATTR3resfail(obj_wcc=obj_wcc)
        result = SETATTR3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_lookup(self, data, cred):
        args = self.nfs3unpacker.unpack_LOOKUP3args()
        self.curr_fh = self.rootfh.lookup(str(args.what.dir.data))
        attributes = self._get_fattr3_attributes()
        post_dir_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        self.curr_fh = self.curr_fh.lookup(str(args.what.name))
        resok = None
        status = NFS3ERR_NOENT
        if self.curr_fh:
            status = NFS3_OK
            attributes = self._get_fattr3_attributes()
            post_obj_file_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
            resok = LOOKUP3resok(object=nfs_fh3(data=self.curr_fh.file), \
                                 obj_attributes=post_obj_file_attr, dir_attributes=post_dir_obj_attr)
        resfail = LOOKUP3resfail(dir_attributes=post_dir_obj_attr)
        result = LOOKUP3res(status=status, resok=resok, resfail=resfail)
        return result

    def nfs3proc_access(self, data, cred):
        args = self.nfs3unpacker.unpack_ACCESS3args()
        self.curr_fh = self.rootfh.lookup(str(args.object.data))
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        status = NFS3_OK
        if not args.access & self.curr_fh.supported_access():
            status = NFS3ERR_ACCES
        resok = ACCESS3resok(obj_attributes=post_obj_attr, access=args.access)
        resfail = ACCESS3resfail(obj_attributes=post_obj_attr)
        result = ACCESS3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_readlink(self, data, cred):
        return None

    def nfs3proc_read(self, data, cred):
        args = self.nfs3unpacker.unpack_READ3args()
        self.curr_fh = self.rootfh.lookup(str(args.file.data))
        buf = self.curr_fh.read(args.offset, args.count)
        attributes = self._get_fattr3_attributes()
        obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        eof = 1
        if (len(buf) < args.count):
            eof = 0
        resok = READ3resok(file_attributes=obj_attr, count=len(buf), eof=eof, data=buf)
        resfail = READ3resfail(file_attributes=obj_attr)
        result = READ3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result
 
    def nfs3proc_write(self, data, cred):
        args = self.nfs3unpacker.unpack_WRITE3args()
        self.curr_fh = self.rootfh.lookup(str(args.file.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        size = self.curr_fh.write(args.offset, args.data, count=args.count,stable=args.stable)
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resok = WRITE3resok(file_wcc=obj_wcc, count=size, committed=args.stable, verf=self.curr_fh.write_verifier)
        resfail = WRITE3resfail(file_wcc=obj_wcc)
        result = WRITE3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_create(self, data, cred):
        args = self.nfs3unpacker.unpack_CREATE3args()
        self.curr_fh = self.rootfh.lookup(str(args.where.dir.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        attr = {}
        if args.how.mode == EXCLUSIVE:
            verf = args.how.verf
        else:
            attr = args.how.obj_attributes
        self.curr_fh.create(args.where.name, mode=args.how.mode, attrs=attr)
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        self.curr_fh = self.curr_fh.lookup(str(args.where.name))
        pfh3_obj = post_op_fh3(handle_follows=TRUE, handle=nfs_fh3(data=self.curr_fh.file))
        attributes = self._get_fattr3_attributes()
        post_obj_file_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        resok = CREATE3resok(obj=pfh3_obj, obj_attributes=post_obj_file_attr, dir_wcc=obj_wcc)
        resfail = CREATE3resfail(dir_wcc=obj_wcc)
        result = CREATE3res(status=NFS3_OK, resok=resok, resfail=resfail) 
        return result

    def nfs3proc_mkdir(self, data, cred):
        args = self.nfs3unpacker.unpack_MKDIR3args()
        self.curr_fh = self.rootfh.lookup(str(args.where.dir.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        attr = {}
        attr = args.attributes

        self.curr_fh.mkdir(args.where.name, attrs=attr)

        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        self.curr_fh = self.curr_fh.lookup(str(args.where.name))
        pfh3_obj = post_op_fh3(handle_follows=TRUE, handle=nfs_fh3(data=self.curr_fh.file))
        attributes = self._get_fattr3_attributes()
        post_obj_file_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        resok = MKDIR3resok(obj=pfh3_obj, obj_attributes=post_obj_file_attr, dir_wcc=obj_wcc)
        resfail = MKDIR3resfail(dir_wcc=obj_wcc)
        result = MKDIR3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_symlink(self, data, cred):
        return None

    def nfs3proc_mknod(self, data, cred):
        return None

    def nfs3proc_remove(self, data, cred):
        args = self.nfs3unpacker.unpack_REMOVE3args()
        self.curr_fh = self.rootfh.lookup(str(args.dir.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        self.curr_fh.remove(args.name)
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resok = REMOVE3resok(dir_wcc=obj_wcc)
        resfail = REMOVE3resfail(dir_wcc=obj_wcc)
        result = REMOVE3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_rmdir(self, data, cred):
        args = self.nfs3unpacker.unpack_RMDIR3args()
        self.curr_fh = self.rootfh.lookup(str(args.dir.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        self.curr_fh.rmdir(args.name)
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resok = RMDIR3resok(dir_wcc=obj_wcc)
        resfail = RMDIR3resfail(dir_wcc=obj_wcc)
        result = RMDIR3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_rename(self, data, cred):
        args = self.nfs3unpacker.unpack_RENAME3args()
        self.curr_fh = self.rootfh.lookup(str(args.fromfile.dir.data))
        attributes = self._get_fattr3_attributes()
        pre_from_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        self.curr_from_fh = self.curr_fh

        self.curr_fh = self.rootfh.lookup(str(args.tofile.dir.data))
        attributes = self._get_fattr3_attributes()
        pre_to_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        self.curr_fh.rename(self.curr_from_fh, args.fromfile.name, args.tofile.name)
        self.curr_fh = self.rootfh.lookup(str(args.fromfile.dir.data))
        attributes = self._get_fattr3_attributes()
        post_from_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)

        self.curr_from_fh = self.curr_fh
        self.curr_fh = self.rootfh.lookup(str(args.tofile.dir.data))
        attributes = self._get_fattr3_attributes()
        post_to_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        from_obj_wcc = wcc_data(before=pre_from_obj_attr, after=post_from_obj_attr)
        to_obj_wcc = wcc_data(before=pre_to_obj_attr, after=post_to_obj_attr)

        resok = RENAME3resok(fromdir_wcc=from_obj_wcc, todir_wcc=to_obj_wcc)
        resfail = RENAME3resfail(fromdir_wcc=from_obj_wcc, todir_wcc=to_obj_wcc)
        result = RENAME3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_link(self, data, cred):
        return None
        
    def nfs3proc_readdir(self, data, cred):
        args = self.nfs3unpacker.unpack_READDIR3args()
        cookie = args.cookie
        cookieverf = args.cookieverf
        count = args.count
        self.curr_fh = self.rootfh.lookup(str(args.dir.data))
        self.dir_fh = self.curr_fh
        try:
            verifier = self.curr_fh.getdirverf()
            if cookie != 0:
                if cookieverf != verifier:
                    return rpc.GARBAGE_ARGS, NFS3ERR_BAD_COOKIE

            try:
                dirlist = self.curr_fh.read_dir(cookie)
            except IndexError:
                return rpc.GARBAGE_ARGS, NFS3ERR_BAD_COOKIE
            entries = []
            bytecnt = 0
            packer = NFS3Packer()
            for entry in dirlist:
                self.curr_fh = entry
                attributes = self._get_fattr3_attributes()
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
                return simple_error(NF34ERR_TOOSMALL)
            # Encode entries as linked list
            e3 = []
            for entry in entries:
                e3 = [entry3(fileid=entry.fattr3_fileid, name=entry.name, cookie=entry.cookie, nextentry=e3)]
            if len(entries) < len(dirlist):
                d3 = dirlist3(entries=e3, eof=0)
            else:
                d3 = dirlist3(entries=e3, eof=1)
        except NFS3Error, e:
            raise
        self.curr_fh = self.dir_fh
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        resok = READDIR3resok(dir_attributes=post_obj_attr, cookieverf=verifier, reply=d3)
        resfail = READDIR3resfail(dir_attributes=post_obj_attr)
        result = READDIR3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_readdirplus(self, data, cred):
        args = self.nfs3unpacker.unpack_READDIRPLUS3args()
        cookie = args.cookie
        cookieverf = args.cookieverf
        dircount = args.dircount
        maxcount = args.maxcount
        self.curr_fh = self.rootfh.lookup(str(args.dir.data))
        self.dir_fh = self.curr_fh
        try:
            verifier = self.curr_fh.getdirverf()
            if cookie != 0:
                if cookieverf != verifier:
                    return rpc.GARBAGE_ARGS, NFS3ERR_BAD_COOKIE

            try:
                dirlist = self.curr_fh.read_dir(cookie)
            except IndexError:
                return rpc.GARBAGE_ARGS, NFS3ERR_BAD_COOKIE
            entries = []
            bytecnt = 0
            packer = NFS3Packer()
            for entry in dirlist:
                # Compute size of XDR encoding
                self.curr_fh = entry
                attributes = self._get_fattr3_attributes()
                name_attributes = post_op_attr(attributes_follow=TRUE, attributes=attributes)
                name_handle = post_op_fh3(handle_follows=TRUE, handle=nfs_fh3(data=self.curr_fh.file))
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
                return simple_error(NF34ERR_TOOSMALL)
            # Encode entries as linked list
            e3 = []
            for entry in entries:
                e3 = [entryplus3(fileid=entry.fattr3_fileid, name=entry.name, cookie=entry.cookie, 
                                name_attributes=entry.attr, name_handle=entry.name_handle, nextentry=e3)]
            if len(entries) < len(dirlist):
                d3 = dirlistplus3(entries=e3, eof=0)
            else:
                d3 = dirlistplus3(entries=e3, eof=1)
        except NFS3Error, e:
            raise
        self.curr_fh = self.dir_fh
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        resok = READDIRPLUS3resok(dir_attributes=post_obj_attr, cookieverf=verifier, reply=d3)
        resfail = READDIRPLUS3resfail(dir_attributes=post_obj_attr)
        result = READDIRPLUS3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_fsstat(self, data, cred):
        return None

    def nfs3proc_fsinfo(self, data, cred):
        args = self.nfs3unpacker.unpack_FSINFOargs()
        self.curr_fh = self.rootfh.lookup(str(args.fsroot.data))
        attributes = self._get_fattr3_attributes()
        obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        resok = FSINFO3resok(obj_attributes=obj_attr,
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

        resfail = FSINFO3resfail(obj_attributes=obj_attr)
        result = FSINFO3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_pathconf(self, data, cred):
        args = self.nfs3unpacker.unpack_PATHCONF3args()
        self.curr_fh = self.rootfh.lookup(str(args.object.data))
        attributes = self._get_fattr3_attributes()
        obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        resok = PATHCONF3resok(obj_attributes=obj_attr,
                               linkmax=0, 
                               name_max=NFS3_FHSIZE,
                               no_trunc=TRUE,
                               chown_restricted=TRUE,
                               case_insensitive=FALSE,
                               case_preserving=TRUE
                              )
        resfail = PATHCONF3resfail(obj_attributes=obj_attr)
        result = PATHCONF3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

    def nfs3proc_commit(self, data, cred):
        args = self.nfs3unpacker.unpack_COMMIT3args()
        self.curr_fh = self.rootfh.lookup(str(args.file.data))
        attributes = self._get_fattr3_attributes()
        pre_obj_attr = pre_op_attr(attributes_follow=TRUE, attributes=attributes)
        self.curr_fh.commit(self, args.offset, args.count)
        attributes = self._get_fattr3_attributes()
        post_obj_attr = post_op_attr(attributes_follow=TRUE, attributes=attributes)
        obj_wcc = wcc_data(before=pre_obj_attr, after=post_obj_attr)
        resok = COMMIT3resok(file_wcc=obj_wcc, verf=self.curr_fh.write_verifier)
        resfail = COMMIT3resfail(file_wcc=obj_wcc)
        result = COMMIT3res(status=NFS3_OK, resok=resok, resfail=resfail)
        return result

def startnfs3server(rootfh, port=2049, host='', pubfh=None, raft = None):
    server = NFS3Server(rootfh, port=port, host=host, pubfh=directory)
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
    logger.debug("Python NFSv4 Server, (c) CITI, Regents of the University of Michigan")
    logger.debug("Starting Server, root handle: %s" % directory)

    server.run()
    try:
        server.unregister()
    except:
        pass

def startup(host, port, directory, raft = None):
    rootfh = HardHandle(None, "/", None, directory)
    nfs = threading.Thread(
           target = startnfs3server,
           kwargs = {'rootfh': rootfh, 
                     'port': port, 
                     'host': host, 
                     'raft': raft
                     }
    )
    nfs.start()

    mnt = threading.Thread(
           target = mnt3server,
           kwargs = {'rootfh': rootfh,
                     'port': 32767, 
                     'host': host}
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
