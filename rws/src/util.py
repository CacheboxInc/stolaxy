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
