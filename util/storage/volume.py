import os
import subprocess
import sys

sys.path.append('../../config')
from config import *
from discover import *

class Volume(object):
    def __init__(self):
        self.discover = Discover()
        self.devices = self.discover.getDevices()

    def initialize(self):

        cmd = (
            "lvdisplay",
            "-C",
            "--noheadings",
            "--separator=,",
            "--units",
            "b"
            )

        lvdisplay = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = lvdisplay.communicate()
        if lvdisplay.returncode != 0:
            print 'WARNING: error running lvdisplay: %s, %s' % (out, err)
            return False

        found = False

        for lvline in out.splitlines():
            lvline = lvline.split(',')
            if lvline[0] == STOLAXY_FLASH_TIER_VOLUME:
                assert lvline[1] == STOLAXY_FLASH_TIER_VOLUME_GROUP
                found = True
                break

        if not found:
            cmd = (
                "lvcreate",
                "-n",
                STOLAXY_FLASH_TIER_VOLUME,
                "-l",
                "100%FREE",
                STOLAXY_FLASH_TIER_VOLUME_GROUP
                )
        else:
            cmd = (
                "lvextend",
                "-l",
                "100%FREE",
                "/dev/%s/%s" % (
                    STOLAXY_FLASH_TIER_VOLUME_GROUP, 
                    STOLAXY_FLASH_TIER_VOLUME)
                )
                
        op = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = op.communicate()
        if op.returncode != 0:
            print 'WARNING: error running lvcreate/lvextend: %s, %s' % (out, err)
            return False

        return True

