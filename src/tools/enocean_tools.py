from typing import Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.common.eep import Eep
from src.common.device_exception import DeviceException
from src.tools.converter import Converter
from src.tools.pickle_tools import PickleTools


class EnoceanTools:

    @classmethod
    def int_to_byte_list(cls, value: int):
        result = []
        for i in range(0, 4):
            result.append(value >> (i * 8) & 0xff)
        result.reverse()
        return result

    @classmethod
    def extract_props(cls, packet: RadioPacket, eep: Eep) -> Dict[str, object]:
        if packet.packet_type != PACKET.RADIO:
            raise DeviceException("no radio paket ({})!".format(cls.packet_type_to_string(packet.packet_type)))

        data = {}
        props = packet.parse_eep(
            rorg_func=eep.func,
            rorg_type=eep.type,
            direction=eep.direction,
            command=eep.command
        )
        for prop_name in props:
            prop = packet.parsed[prop_name]
            data[prop_name] = prop['raw_value']
        return data

    @classmethod
    def packet_type_to_string(cls, packet_type):
        if type(packet_type) == int:
            for e in PACKET:
                if packet_type == e:
                    return e.name
        elif type(packet_type) == PACKET:
            return packet_type.name
        return str(packet_type)

    @classmethod
    def log_pickled_enocean_packet(cls, logger_func, packet, text):
        logger_func(
            "%s - packet: %s; sender: %s; dest: %s; RORG: %s; dump:\n%s",
            text,
            EnoceanTools.packet_type_to_string(packet.packet_type),
            Converter.to_hex_string(packet.sender_int),
            Converter.to_hex_string(packet.destination_int),
            Converter.to_hex_string(packet.rorg),
            PickleTools.pickle_packet(packet)
        )

    @classmethod
    def extract_packet_props(cls, packet, eep):
        """
        :param enocean.protocol.packet.RadioPacket packet:
        :param Eep eep:
        :rtype: dict{str, object}
        """
        if packet.rorg == eep.rorg:
            try:
                data = EnoceanTools.extract_props(packet=packet, eep=eep)
            except AttributeError as ex:
                raise DeviceException(ex)
        else:
            data = {}

        return data
