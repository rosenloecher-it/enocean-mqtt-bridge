from enocean.protocol.constants import PACKET


class EnoceanTools:

    @classmethod
    def int_to_byte_list(cls, value: int, list_length: int):
        result = []
        for i in range(0, 4):
            result.append(value >> (i * 8) & 0xff)
        result.reverse()
        return result

    @classmethod
    def extract_packet(cls, packet, rorg_func, rorg_type, direction=None, command=None):
        """
        :param enocean.protocol.packet.RadioPacket packet:
        :rtype: dict{str, object}
        """
        data = {}
        props = packet.parse_eep(
            rorg_func=rorg_func,
            rorg_type=rorg_type,
            direction=direction,
            command=command
        )
        for prop_name in props:
            prop = packet.parsed[prop_name]
            data[prop_name] = prop['raw_value']
        return data

    @classmethod
    def extract_packet_type_text(cls, packet_type):
        if type(packet_type) == int:
            for e in PACKET:
                if packet_type == e:
                    return e.name
        elif type(packet_type) == PACKET:
            return packet_type.name
        return str(packet_type)
