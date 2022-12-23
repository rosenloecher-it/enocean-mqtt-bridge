from enum import Enum, IntEnum
from typing import Optional, Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.common.device_exception import DeviceException
from src.common.eep import Eep
from src.enocean_packet_factory import EnoceanPacketFactory
from src.common.eep_prop_exception import EepPropException
from src.tools.enocean_tools import EnoceanTools


class RockerPress(Enum):
    RELEASE = "RELEASE"
    PRESS_SHORT = "SHORT"  # presset
    PRESS_LONG = "LONG"  # pressed

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name


class RockerButton(IntEnum):
    """
    button ids to location: <above>
        [1] [3]
        [0] [2]
    works together as direction switch: 0 with 1; 2 with 3
    """
    ROCK0 = 0  # usually OFF (left side)
    ROCK1 = 1  # usually ON (left side)
    ROCK2 = 2  # usually OFF (right side)
    ROCK3 = 3  # usually ON (right side)

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name

    @classmethod
    def convert(cls, num: int):
        for e in cls:
            if e.value == num:
                return e

        return None


class RockerAction:

    def __init__(self, press: RockerPress = None, button: RockerButton = None, is_error=False):
        self.press = press
        self.button = button
        self.is_error = is_error

    def __str__(self):
        if self.button is None:
            return '{}'.format(repr(self.press))
        else:
            return '{}-{}'.format(repr(self.press), repr(self.button))

    def __repr__(self) -> str:
        if self.button is None:
            return '{}({})'.format(self.__class__.__name__, repr(self.press))
        else:
            return '{}({}-{})'.format(self.__class__.__name__, repr(self.press), repr(self.button))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.press == other.press and self.button == other.button

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.__class__.__name__, self.press, self.button))


class RockerSwitchTools:

    DEFAULT_EEP = Eep(
        rorg=0xf6,
        func=0x02,
        type=0x02,
        direction=None,
        command=None
    )

    EMPTY_PROPS = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}

    @classmethod
    def create_packet(cls, action: RockerAction,
                      destination: Optional[int] = None, sender: Optional[int] = None,
                      learn=False) -> RadioPacket:
        props = cls.create_props(action)

        packet = EnoceanPacketFactory.create_packet(
            eep=cls.DEFAULT_EEP, destination=destination, sender=sender, learn=learn, **props
        )

        return packet

    @classmethod
    def create_props(cls, action: RockerAction) -> Dict[str, int]:
        if action.press in [RockerPress.PRESS_SHORT, RockerPress.PRESS_LONG]:
            if action.button is None:
                raise ValueError("no RockerSwitchButton defined!")
            if action.press == RockerPress.PRESS_LONG:
                props = {'R1': 0, 'EB': 0, 'R2': action.button.value, 'SA': 1, 'T21': 1, 'NU': 1}
            else:  # short
                props = {'R1': action.button.value, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        elif action.press == RockerPress.RELEASE:
            props = cls.EMPTY_PROPS
        else:
            raise ValueError()

        return props

    @classmethod
    def extract_props(cls, packet: RadioPacket) -> Dict:
        eep = cls.DEFAULT_EEP
        if packet.packet_type == PACKET.RADIO and packet.rorg == eep.rorg:
            try:
                data = EnoceanTools.extract_props(packet=packet, eep=eep)
            except AttributeError as ex:
                raise DeviceException(ex)
        else:
            data = {}

        return data

    @classmethod
    def extract_action_from_packet(cls, packet: RadioPacket) -> RockerAction:
        props = cls.extract_props(packet)
        return cls.extract_action(props)

    @classmethod
    def extract_action(cls, data: Dict) -> RockerAction:
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 1, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}"
        action = RockerAction()

        try:
            if data["SA"] == 1:
                action.press = RockerPress.PRESS_LONG
                action.button = RockerButton.convert(data["R2"])
            elif data["EB"] == 1:
                action.press = RockerPress.PRESS_SHORT
                action.button = RockerButton.convert(data["R1"])
            elif data == cls.EMPTY_PROPS:
                action.press = RockerPress.RELEASE
                action.button = None
            else:
                raise EepPropException("no proper rocker data ({})!".format(str(data)))

            return action

        except AttributeError as ex:  # TODO handle index errors
            raise EepPropException("no proper rocker data ('{}' in ({}))!".format(str(ex), str(data)), ex)
