import os
import subprocess

from config import *
from discover import *

class Volume(object):
    def __init__(self):
        self.discover = Discover()
        self.devices = self.discover.getDevices()

    def initialize(self):
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
