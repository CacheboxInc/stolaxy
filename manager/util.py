def getusize(size):
    """
    return a user friendly size string
    """

    if size >= 1 << 40:
        return '%0.2f TB' % (size * 1.0 / (1 << 40))
    elif size >= 1 << 30:
        return '%0.2f GB' % (size * 1.0 / (1 << 30))
    elif size >= 1 << 20:
        return '%0.2f MB' % (size * 1.0 / (1 << 20))
    elif size >= 1 << 10:
        return '%0.2f KB' % (size * 1.0 / (1 << 10))
    else:
        return str(size) + ' B'


def usize2int(usize):
	"""
	given a user friendly size string, specified by te user, e.g 100g or 100gb, 
	return an integer equivalent
	"""

	usize = usize.upper()
	if 'K' in usize or 'M' in usize:
		raise Exception("will not support anything less than GB")

	multiplier = 1
	if 'G' in usize or 'GB' in usize:
		multiplier = 1 << 30
	elif 'T' in usize or 'TB' in usize:
		multiplier = 1 << 40
	elif 'P' in usize or 'PB' in usize:
		multiplier = 1 << 50

	for i, j in enumerate(usize):
		if j.isdigit():
			continue

		break

	return int(usize[:i]) * multiplier

if __name__ == '__main__':
	assert usize2int('100g') == 100 * (1 << 30)
	assert usize2int('100 gb') == 100 * (1 << 30)
