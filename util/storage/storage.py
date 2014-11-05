import os
import subprocess
from discover import *

STOLAXY_FLASH_TIER_VOLUME_GROUP = 'stolaxy_flash_vg'
STOLAXY_FLASH_TIER_VOLUME = 'stolaxy_flash_vol01'
STOLAXY_BACKEND_XFS_FLASH_TIER = "/stolaxy_flash_tier"
STOLAXY_FLASH_VOLUME_PATH = "/dev/%s/%s" % (STOLAXY_FLASH_TIER_VOLUME_GROUP, STOLAXY_FLASH_TIER_VOLUME)

class Storage(object):
    def __init__(self):
        self.discover = Discover()
        self.devices = self.discover.getDevices()

    def initialize_volume(self):
        """
        create STOLAXY_FLASH_TIER_VOLUME if it does not exist and add
        newly discovered flash devices
        """

        cmd = (
            "vgdisplay", 
            "-C",
            "--noheadings",
            "--separator=,",
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
            "--separator=,",
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

        flash_devices = []
        device_types = self.discover.discover(newdevices)
        for device, iops, type in device_types:
            if type == 'FLASH':
                flash_devices.append(device)

        if not found and len(flash_devices) == 0:
            print 'ERROR: insufficient storage. please provision flash based devices and restart.'
            return
        elif found and len(flash_devices) == 0:
            print 'INFO: initialized stolaxy storage subsystem successfully. no new devices detected.'
            return

        
        if not found:
            cmd = [
                "vgcreate",
                STOLAXY_FLASH_TIER_VOLUME_GROUP
                ]
            cmd += flash_devices
        else:
            cmd = [
                "vgextend",
                STOLAXY_FLASH_TIER_VOLUME_GROUP
                ]
            
            cmd += flash_devices
            
        op = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = op.communicate()
        if op.returncode != 0:
            print 'WARNING: error running vgcreate/vgextend: %s, %s' % (out, err)
            return

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

    def initialize_backendfilesystem(self):
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
        
    def initialize(self):
        self.initialize_volume()
        self.initialize_backendfilesystem()

        print 'storage initialized successfully.'
        
if __name__ == '__main__':
    storage = Storage()
    storage.initialize()
