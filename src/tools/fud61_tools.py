from typing import Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.device.rocker_actor import StateValue
from src.eep import Eep
from src.tools.device_exception import DeviceException
from src.tools.enocean_tools import EnoceanTools


class Fud61Message:

    def __init__(self, rssi=None, switch_state: StateValue = None, dim_value: int = None):
        self.rssi = rssi
        self.switch_state = switch_state
        self.dim_value = dim_value


class Fud61Tools:

    DEFAULT_EEP = Eep(
        rorg=0xa5,
        func=0x38,
        type=0x08,
        direction=None,
        command=0x02
    )

    @classmethod
    def extract_props(cls, packet: RadioPacket) -> Dict:
        eep = cls.DEFAULT_EEP
        if packet.packet_type == PACKET.RADIO and packet.rorg == eep.rorg:
            try:
                data = EnoceanTools.extract_props(packet=packet, eep=eep)
                if hasattr(packet, "dBm"):
                    data["rssi"] = packet.dBm
            except AttributeError as ex:
                raise DeviceException(ex)
        else:
            data = {}

        return data

    @classmethod
    def extract_message_from_packet(cls, packet: RadioPacket) -> Fud61Message:
        props = cls.extract_props(packet)
        return cls.extract_message(props)

    @classmethod
    def extract_message(cls, data: Dict) -> Fud61Message:
        message = Fud61Message()

        message.rssi = data.get("rssi")
        message.switch_state = cls.extract_switch_value(data.get("SW"))
        message.dim_state = cls.extract_dim_value(value=data.get("EDIM"), range=data.get("EDIMR"))

        return message

    @classmethod
    def extract_switch_value(cls, value):
        if value == 1:
            return StateValue.ON
        elif value == 0:
            return StateValue.OFF
        else:
            return StateValue.ERROR

    @classmethod
    def extract_dim_value(cls, value, range):
        if value is None:
            return None
        if range == 0:
            return value
        elif range == 1:
            return int(value / 256 + 0.5)
        else:
            return None
