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

def generate_random_password():
    """
    Generate random password for new user.
    It should satisfy following conidtions:
    1) min length: at least 8 characters.
    2) must have lower case letter.
    3) must have upper case letter.
    4) contain numbers.
    """
    import random
    import string
    LENGTH = 10
    pwd = ''.join(random.choice(string.ascii_uppercase + string.digits + \
                 string.ascii_lowercase) for _ in range(LENGTH))
    return pwd

def generate_encrypted_password(raw_password=None):
     """
     Generate secure password for new account created by admin.
     algorithm used: sha1

     """

     import random
     import hashlib

     rand1 = str(random.random()).encode('utf-8')
     rand2 = str(random.random()).encode('utf-8')
     salt  = hashlib.sha1(rand1 + rand2).hexdigest()[:10]
     hsh   = hashlib.sha1(salt.encode('utf-8') +  raw_password.encode('utf-8')).hexdigest()
     pwd   = '%s$%s' % (salt, hsh)
     return pwd

def generate_password(raw_password=None):
    """
    Method to generate user's password.

    """

    if raw_password is None:
        raw_password = generate_random_password()

    return generate_encrypted_password(raw_password)

def check_password(raw_password, encrypted_pwd):
    """
    Method to check whether password supplied by user 
    is correct or not.

    """
    import random
    import hashlib

    salt, hsh = encrypted_password.split('$')
    hsh_raw = hashlib.sha1(salt.encode('utf-8') + raw_password.encode('utf-8')).hexdigest()
    return hsh == hsh_raw

if __name__ == '__main__':
	assert usize2int('100g') == 100 * (1 << 30)
	assert usize2int('100 gb') == 100 * (1 << 30)
