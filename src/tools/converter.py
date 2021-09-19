

class Converter:

    @classmethod
    def to_hex_string(cls, data):
        if data is None:
            return "null"
        ''' Convert list of integers to a hex string, separated by ":" '''
        if isinstance(data, int):
            return '%02X' % data
        return ':'.join([('%02X' % o) for o in data])
