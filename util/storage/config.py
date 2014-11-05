STOLAXY_FLASH_TIER_VOLUME_GROUP = 'stolaxy_flash_vg'
STOLAXY_FLASH_TIER_VOLUME = 'stolaxy_flash_vol01'
STOLAXY_BACKEND_XFS_FLASH_TIER = "/stolaxy_flash_tier"
STOLAXY_FLASH_VOLUME_PATH = "/dev/%s/%s" % (STOLAXY_FLASH_TIER_VOLUME_GROUP, STOLAXY_FLASH_TIER_VOLUME)

# the minimum number of random read iops for a device to be classified
# as being flash based.

FLASH_RAND_READ_IOPS = 20000
