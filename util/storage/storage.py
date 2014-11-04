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
        for vgline in out.splitlines():
            vgline = vgline.strip().split(',')
            vgname = vgline[0]
            if vgname == STOLAXY_FLASH_TIER_VOLUME_GROUP:
                found = True
                break
            
        #
        # ignore all devices which are either already a part of the
        # FLASH_TIER_VOLUME_GROUP or a different volume group
        #

        cmd = (
            "pvdisplay",
            "-C",
            "--noheadings",
            "--separator=','",
            "--units",
            "b"
            )
        
        pvdisplay = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = pvdisplay.communicate()
        if pvdisplay.returncode != 0:
            print 'WARNING: error running pvdisplay: %s, %s' % (out, err)
            return

        existing = []
        for pvline in out.splitlines():
            pvline = pvline.strip().split(',')
            device = pvline[0]
            vg = pvline[1]
            existing.append(device)
            
        newdevices = []
        for device in self.devices:
            if device in existing:
                continue
            
            newdevices.append(device)

        if not found and len(newdevices) == 0:
            print 'ERROR: insufficient storage. please provision flash based devices and restart'
            return

        if not found:
            cmd = (
                "vgcreate",
                STOLAXY_FLASH_TIER_VOLUME_GROUP,
                ' '.join(newdevices)
                )
        else:
            cmd = (
                "vgextend",
                STOLAXY_FLASH_TIER_VOLUME_GROUP,
                ' '.join(newdevices)
                )
            
        op = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = op.communicate()
        if op.returncode != 0:
            print 'WARNING: error running vgcreate/vgextend: %s, %s' % (out, err)
            return

        # TBD. create volume 

        cmd = (
            "lvdisplay",
            "-C",
            "--noheadings",
            "--separator=','",
            "--units",
            "b"
            )

        lvdisplay = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = lvdisplay.communicate()
        if lvdisplay.returncode != 0:
            print 'WARNING: error running lvdisplay: %s, %s' % (out, err)
            return

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
            return
        print 'storage layer initialized successfully'
        
if __name__ == '__main__':
    storage = Storage()
    storage.initialize()
