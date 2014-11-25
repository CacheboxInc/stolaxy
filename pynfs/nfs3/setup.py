#!/usr/bin/env python

DESCRIPTION = """\
pynfs is a collection of tools and libraries for NFS3. It includes
a NFS3 library and a server test application.
"""

import sys
import os
import glob
from distutils.dep_util import newer_group

topdir = os.getcwd()
if  __name__ == "__main__":
    sys.path.insert(1, os.path.join(topdir, 'lib'))
    os.system("gcc -shared -o ./portmap.so -fPIC -I/usr/include/python2.7 -lpython2.7 ./portmap.c")

import rpcgen

def needs_updating(xdrfile):
    gen_path = os.path.join(topdir, 'lib', 'rpcgen.py')
    name_base = xdrfile[:xdrfile.rfind("xdrdef")]
    sources = [gen_path, xdrfile]
    targets = [ name_base + "_const.py",
                name_base + "_type.py",
                name_base + "_pack.py" ]
    for t in targets:
        if newer_group(sources, t):
            return True
    return False

def use_xdr(dir, xdrfile):
    """Move to dir, and generate files based on xdr file"""
    os.chdir(dir)
    if needs_updating(xdrfile):
        rpcgen.run(xdrfile)
        for file in glob.glob(os.path.join(dir, 'parse*')):
            print "deleting", file
            os.remove(file)

def generate_files():
    home = os.getcwd()
    use_xdr("%s/xdrdef" % topdir, 'nfs3.x')
    sources = [ os.path.join(topdir, 'lib', 'ops_gen.py'),
                'xdrdef.nfs3_const.py', 'xdrdef.nfs3_type.py' ]
    dir = os.path.join(topdir, 'lib', 'rpc')
    use_xdr(dir, 'rpc.x')
    dir = os.path.join(topdir, 'lib', 'rpc', 'rpcsec')
    use_xdr(dir, 'gss.x')

    use_xdr("%s/xdrdef" % topdir, 'mnt3.x')
    sources = [ os.path.join(topdir, 'lib', 'ops_gen.py'),
                'xdrdef.mnt3_const.py', 'xdrdef.mnt3_type.py' ]
    dir = os.path.join(topdir, 'lib', 'rpc')
    use_xdr(dir, 'rpc.x')
    dir = os.path.join(topdir, 'lib', 'rpc', 'rpcsec')
    use_xdr(dir, 'gss.x')
    os.chdir(home)

# FRED - figure how to get this to run only with build/install type command
generate_files()
