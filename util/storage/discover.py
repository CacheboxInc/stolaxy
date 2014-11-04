"""
discover storage managed by stolaxy. at the moment we implement a pure
flash tier, so we limit ourselves to the discovery of flash drives and
volumes.
"""

import sys

MIN_RAND_READ_IOPS = 20000

def discover():
    """
    find all non device mapper devices which can do >
    MIN_RAND_READ_IOPS and return them as a list of (device,
    detected_iops, type) tuples. type is one of RAM, FLASH or HDD
    """

    return []
