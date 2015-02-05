import os
import subprocess
import sys

sys.path.append('../../config')

from config import *
from discover import *

"""
Discovers all drives attached to the machine and creates volume groups with appropriate tiers e.g. HDD tier, Flash tier.
"""

class VolumeGroup(object):
    def __init__(self):
        self.discover = Discover()
        self.devices = self.discover.getDevices()

    def initialize(self, vgroup):
        """
        create vgroup if it does not exist and add
        newly discovered devices of the corresponding type
        """

        assert vgroup in (STOLAXY_FLASH_TIER_VOLUME_GROUP, STOLAXY_HDD_TIER_VOLUME_GROUP)

        print "initializing %s volume group" % vgroup

        if vgroup == STOLAXY_FLASH_TIER_VOLUME_GROUP:
            dtype = 'FLASH'
        elif vgroup == STOLAXY_HDD_TIER_VOLUME_GROUP:
            dtype = 'HDD'
        else:
            assert 0, "Unknown volume group type specified"
            
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
            return False

        found = False
        for vgline in out.splitlines():
            vgline = vgline.strip().split(',')
            vgname = vgline[0]
            if vgname == vgroup:
                found = True
                break
            
        #
        # ignore all devices which are either already a part of
        # vgroup or a different volume group
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
            return False

        existing = []
        for pvline in out.splitlines():
            pvline = pvline.strip().split(',')
            device = pvline[0]
            vg = pvline[1].strip()
            if len(vg) == 0:
                continue

            existing.append(device)
            
        newdevices = []
        for device in self.devices:
            if device in existing:
                continue
            
            newdevices.append(device)

        devices = []
        device_types = self.discover.discover(newdevices)
        for device, iops, type in device_types:
            if type == dtype:
                devices.append(device)

        if not found and len(devices) == 0:
            print 'ERROR: insufficient storage. please provision devices and restart.'
            return False
        elif found and len(devices) == 0:
            print 'INFO: initialized stolaxy storage subsystem successfully. no new devices detected.'
            return True
        
        if not found:
            cmd = [
                "vgcreate",
                vgroup
                ]
            cmd += devices
        else:
            cmd = [
                "vgextend",
                vgroup
                ]
            
            cmd += devices
            
        op = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = op.communicate()
        if op.returncode != 0:
            print 'WARNING: error running vgcreate/vgextend: %s, %s' % (out, err)
            return False

        return True


if __name__ == '__main__':
    vg = VolumeGroup()
    vg.initialize('stolaxy_flash_vg')
    vg.initialize('stolaxy_hdd_vg')
