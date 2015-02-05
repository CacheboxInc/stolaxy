import os
import subprocess
import sys

sys.path.append('../../config')
from config import *

class Filesystem(object):
    def do_mount(self):
        mountcmd = (
            "mount",
            "-t",
            "xfs",
            STOLAXY_FLASH_VOLUME_PATH,
            STOLAXY_BACKEND_XFS_FLASH_TIER
            )

        mount = subprocess.Popen(mountcmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = mount.communicate()
        return mount.returncode

    def initialize(self):
        mounts = open("/proc/mounts").read()
        if STOLAXY_BACKEND_XFS_FLASH_TIER in mounts:
            return True

        r = os.system("mkdir -p %s" % STOLAXY_BACKEND_XFS_FLASH_TIER)
        if r != 0:
            return False

        if self.do_mount() != 0:
            print 'initial mount failed. creating xfs'

            cmd = (
                "mkfs.xfs",
                STOLAXY_FLASH_VOLUME_PATH,
                )

            mkfs = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            out, err = mkfs.communicate()
            if mkfs.returncode != 0:
                print 'mkfs.xfs failed! %s %s' % (out, err)
                return False

            if self.do_mount() != 0:
                print 'aborting as i could not mount xfs filesystem'
                return False

        cmd = (
            "xfs_growfs",
            "-d",
            STOLAXY_BACKEND_XFS_FLASH_TIER
            )

        growfs = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = growfs.communicate()
        if growfs.returncode != 0:
            print 'xfs_growfs failed! %s %s' % (out, err)
            return False

        return True
