import subprocess
from discover import *

STOLAXY_FLASH_TIER_VOLUME_GROUP = 'stolaxy_flash_vg'
STOLAXY_FLASH_TIER_VOLUME = 'stolaxy_flash_vol01'

class Storage(object):
    def __init__(self):
        self.devices = discover()

    def discover(self):
        self.devices = discover()

    def initialize(self):
        """
        create STOLAXY_FLASH_TIER_VOLUME if it does not exist and add
        newly discovered flash devices
        """

        cmd = (
            "vgdisplay", 
            "-C",
            "--noheadings",
            "--separator=','",
            "--nosuffix",
            "--units",
            "b"
            )

        vgdisplay = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = vgdisplay.communicate()
        if vgdisplay.returncode != 0:
            print 'WARNING: error running vgdisplay: %s, %s' % (out, err)
            return

        found = False
        for vgline in out.split('\n'):
            vgline = vgline.strip().split(',')
            vgname = vgline[0]
            if vgname == STOLAXY_FLASH_TIER_VOLUME_GROUP:
                found = True
                break
            
        if not found:
            print 'creating %s' % STOLAXY_FLASH_TIER_VOLUME_GROUP

        for device in self.devices:
            pass
            

if __name__ == '__main__':
    storage = Storage()
    storage.initialize()
