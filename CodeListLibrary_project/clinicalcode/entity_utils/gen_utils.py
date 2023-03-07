def parse_int(value, default=0):
    '''
        Attempts to parse an int from a value, if it fails to do so, returns the default value
    '''
    try:
        return int(value)
    except ValueError:
        return default