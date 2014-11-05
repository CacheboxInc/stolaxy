"""
discover storage managed by stolaxy. at the moment we implement a pure
flash tier, so we limit ourselves to the discovery of flash drives and
volumes.
"""

import subprocess
import sys

FLASH_RAND_READ_IOPS = 20000

class Discover(object):

    def getRandReadIOPS(self, disk):
	type_val=None	
    	try:

		# Even if a device is system dependent, some of it's 
		# partitons may not belong to system dependent 
		# devices and so we also need to determine the tier type
		# for disks those hold system dependent parttions 

		# If the device belongs to AWS ephemeral class then 
		# straightforward declare device as SSD

            cmd = (
                "./cbperf",
                disk,
                "-q",
                "32",
                "-t",
                "30"
             	)

            iops = 0
            r = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = r.communicate()
            if r.returncode != 0:
                return None

            for i in output.splitlines():
                arr = i.split("=")
                if arr[0] == "iops":
                    iops = int(arr[1])
				
                return iops

	except OSError:
            return None


    def getDeviceMapperMajor(self):
        devices = open("/proc/devices").readlines()
        for device in devices:
            if 'device-mapper' in device:
                return int(device.split()[0])

        return None

    def getMounts(self):
        mounts = open("/proc/mounts").readlines()
        nmounts = []
        for mount in mounts:
            device = mount.split()[0]
            cmd = (
                "readlink",
                "-f",
                device
                )
            
            readlink = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            out, err = readlink.communicate()
            if readlink.returncode == 0:
                nmounts.append(out.strip())
            
        return nmounts

    def getDevices(self):
        dmmajor = self.getDeviceMapperMajor()
        devices = []
        delete = False
        mounts = self.getMounts()
        partitions = open("/proc/partitions").readlines()[2:]
        for partition in partitions:
            major, minor, size, dev = partition.split()
            device = '/dev/%s' % dev
            if int(minor) % 16 != 0 or major == dmmajor or 'sr' in device or device in mounts:
                if delete:
                    devices.pop()
                    delete = False
                continue

            devices.append(device)
            delete = True
            
            #print major, minor, size, device

        return devices
            
    def discover(self, devices):
        """
        find all non device mapper devices which can do >
        MIN_RAND_READ_IOPS and return them as a list of (device,
        detected_iops, type) tuples. type is one of RAM, FLASH or HDD
        """
        
        device_types = []
        
        for device in devices:
            iops = self.getRandReadIOPS(device)
            if iops < FLASH_RAND_READ_IOPS:
                type = 'HDD'
            else:
                type = 'FLASH'

            device_types.append((device, iops, type))

        return device_types

if __name__ == '__main__':
    discover = Discover()
    print discover.discover(('/dev/sdb', '/dev/sda'))
