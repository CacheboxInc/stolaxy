#!/usr/bin/env python
# nfs3lib.py - NFS3 library for Python
#
# Requires python 2.3
# 
# Written by Fred Isaman <iisaman@citi.umich.edu>
# Copyright (C) 2004 University of Michigan, Center for 
#                    Information Technology Integration
#
# Based on version
# Written by Peter Astrand <peter@cendio.se>
# Copyright (C) 2001 Cendio Systems AB (http://www.cendio.se)
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License. 
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


import rpc
import threading
from xdrlib import Error as XDRError
import nfs3_const
from nfs3_const import *
import nfs3_type
from nfs3_type import *
import nfs3_pack
import nfs3_ops
import time
import struct
import socket
import sys
import re

class NFSException(rpc.RPCError):
    pass

class BadCompoundRes(NFSException):
    """The COMPOUND procedure returned some kind of error, ie is not NFS3_OK"""
    def __init__(self, operation, errcode, msg=None):
        self.operation = operation
        self.errcode = errcode
        if msg:
            self.msg = msg + ': '
        else:
            self.msg = ''
    def __str__(self):
        if self.operation is None:
            return self.msg + "empty compound return with status %s" % \
                   nfsstat3[self.errcode]
        else:
            return self.msg + \
                   "operation %s should return NFS3_OK, instead got %s" % \
                   (nfs_opnum3[self.operation], nfsstat3[self.errcode])

class UnexpectedCompoundRes(NFSException):
    """The COMPOUND procedure returned OK, but had unexpected data"""
    def __init__(self, msg=""):
        self.msg = msg
    
    def __str__(self):
        if self.msg:
            return "Unexpected COMPOUND result: %s" % self.msg
        else:
            return "Unexpected COMPOUND result"

class InvalidCompoundRes(NFSException):
    """The COMPOUND return is invalid, ie response is not to spec"""
    def __init__(self, msg=""):
        self.msg = msg
    
    def __str__(self):
        if self.msg:
            return "Invalid COMPOUND result: %s" % self.msg
        else:
            return "Invalid COMPOUND result"

class FancyNFS3Packer(nfs3_pack.NFS3Packer):
    """Handle fattr3 and dirlist3 more cleanly than auto-generated methods"""
    def filter_bitmap3(self, data):
        out = []
        while data:
            out.append(data & 0xffffffffL)
            data >>= 32
        return out

    def filter_fattr3(self, data):
        """Allow direct encoding of dict, instead of opaque attrlist"""
        if type(data) is dict:
            data = dict2fattr(data)
        return data

 
class FancyNFS3Unpacker(nfs3_pack.NFS3Unpacker):
    def filter_bitmap3(self, data):
        """Put bitmap into single long, instead of array of 32bit chunks"""
        out = 0L
        shift = 0
        for i in data:
            out |= (long(i) << shift)
            shift += 32
        return out

    def filter_fattr3(self, data):
        """Return as dict, instead of opaque attrlist"""
        return fattr2dict(data)

    
    def filter_dirlist3(self, data):
        """Return as simple list, instead of strange chain structure"""
        e = data.entries
        if not e:
            return data
        array = [e[0]]
        while e[0].nextentry:
            e = e[0].nextentry
            array.append(e[0])
        data.entries = array
        return data

def _getname(owner, path):
    if path is None:
        return owner
    else:
        return '/' + '/'.join(path)

def check_result(res, msg=None):
    """Verify that a COMPOUND call was successful,
    raise BadCompoundRes otherwise
    """
    if not res.status:
        return

    # If there was an error, it should be the last operation.
    if res.resarray:
        resop = res.resarray[-1].resop
    else:
        resop = None
    raise BadCompoundRes(resop, res.status, msg)

def get_attr_name(bitnum):
    """Return string corresponding to attribute bitnum"""
    return get_bitnumattr_dict().get(bitnum, "Unknown_%r" % bitnum)

_cache_attrbitnum = {} 
def get_attrbitnum_dict():
    """Get dictionary with attribute bit positions.

    Note: This function uses introspection. It assumes an entry
    in nfs3_const.py is an attribute iff it is named FATTR3_<something>. 

    Returns {"type": 1, "fh_expire_type": 2,  "change": 3 ...}
    """
    
    if _cache_attrbitnum:
        return _cache_attrbitnum
    for name in dir(nfs3_const):
        if name.startswith("FATTR3_"):
            value = getattr(nfs3_const, name)
            # Sanity checking. Must be integer. 
            assert(type(value) is int)
            attrname = name[7:].lower()
            _cache_attrbitnum[attrname] = value
    return _cache_attrbitnum

_cache_bitnumattr = {}
def get_bitnumattr_dict():
    """Get dictionary with attribute bit positions.
    
    Note: This function uses introspection. It assumes an entry
    in nfs3_const.py is an attribute iff it is named FATTR3_<something>. 
    Returns { 1: "type", 2: "fh_expire_type", 3: "change", ...}
    """

    if _cache_bitnumattr:
        return _cache_bitnumattr
    for name in dir(nfs3_const):
        if name.startswith("FATTR3_"):
            value = getattr(nfs3_const, name)
            # Sanity checking. Must be integer. 
            assert(type(value) is int)
            attrname = name[7:].lower()
            _cache_bitnumattr[value] = attrname
    return _cache_bitnumattr

def get_attrpackers(packer):
    """Get dictionary with attribute packers of form {bitnum:function}

    Note: This function uses introspection. It depends on that nfs3_pack.py
    has methods for every packer.pack_<attribute>.
    """
    out = {}
    dict = get_attrbitnum_dict()
    for name in dir(nfs3_pack.NFS3Packer):
        if name.startswith("pack_"):
            # pack_ 6 chars. 
            attrname = name[5:]
            out[dict[attrname]] = getattr(packer, name)
    return out

def get_attrunpacker(unpacker):
    """Get dictionary with attribute unpackers of form {bitnum:funct}

    Note: This function uses introspection. It depends on that nfs3_pack.py
    has methods for every unpacker.unpack_<attribute>.

    """
    attrunpackers = {}
    for name in dir(FancyNFS3Unpacker):
        if name.startswith("unpack_"):
            # unpack_ is 8 chars. 
            attrname = name[7:]
            bitnum = get_attrbitnum_dict()[attrname]
            attrunpackers[bitnum] = getattr(unpacker, name)

    return attrunpackers

_cache_packer = FancyNFS3Packer()
_cache_attrpackers = get_attrpackers(_cache_packer)

def dict2fattr(dict):
    """Convert a dictionary of form {numb:value} to a fattr3 object.

    Returns a fattr3 object.  
    """

    attrs = dict.keys()
    attrs.sort()

    attr_vals = ""
    packer = _cache_packer
    attrpackers = _cache_attrpackers

    for attr in attrs:
        value = dict[attr]
        packerfun = attrpackers[attr];
        packer.reset()
        packerfun(value)
        attr_vals += packer.get_buffer()
    attrmask = list2bitmap(attrs)
    return fattr3(attrmask, attr_vals); 

def fattr2dict(obj):
    """Convert a fattr3 object to a dictionary with attribute name and values.

    Returns a dictionary of form {bitnum:value}
    """

    result = {}
    unpacker = FancyNFS3Unpacker(obj.attr_vals)
    list = bitmap2list(obj.attrmask)
    for bitnum in list:
        result[bitnum] = get_attrunpacker(unpacker)[bitnum]()
    unpacker.done()
    return result

def list2bitmap(list):
    """Construct a bitmap from a list of bit numbers"""
    mask = 0L
    for bit in list:
        mask |= 1L << bit
    return mask

def bitmap2list(bitmap):
    """Return (sorted) list of bit numbers set in bitmap"""
    out = []
    bitnum = 0
    while bitmap:
        if bitmap & 1:
            out.append(bitnum)
        bitnum += 1
        bitmap >>= 1
    return out

def parse_nfs_url(url):
    """Parse [nfs://]host:port/path, format taken from rfc 2224
       multipath addr:port pair are as such:

      $ip1:$port1,$ip2:$port2..

    Returns triple server, port, path.
    """
    p = re.compile(r"""
    (?:nfs://)?               # Ignore an optionally prepended 'nfs://'
    (?P<servers>[^/]+)
    (?P<path>/.*)?            # set path=everything else, must start with /
    $
    """, re.VERBOSE)

    m = p.match(url)
    if m:
        servers = m.group('servers')
        server_list = []

        for server in servers.split(','):
            server = server.strip()

            idx = server.rfind(':')
            bracket_idx = server.rfind(']')

            # the first : is before ipv6 addr ] -> no port specified
            if bracket_idx > idx:
                idx = -1

            if idx >= 0:
                host = server[:idx]
                port = server[idx+1:]
            else:
                host = server
                port = None

            # remove brackets around IPv6 addrs, if they exist
            if host.startswith('[') and host.endswith(']'):
                host = host[1:-1]

            port = (2049 if not port else int(port))
            server_list.append((host, port))

        path = m.group('path')
        return tuple(server_list), path
    else:
        raise ValueError("Error parsing NFS URL: %s" % url)
