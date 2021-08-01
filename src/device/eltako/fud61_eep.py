import copy
from enum import IntEnum, Enum
from typing import Dict, Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket


from src.common.eep import Eep
from src.common.switch_state import SwitchState
from src.enocean_packet_factory import EnoceanPacketFactory
from src.common.eep_prop_exception import EepPropException
from src.tools.enocean_tools import EnoceanTools


class Fud61Command(IntEnum):
    STATUS_REQUEST = 0
    DIMMING = 2


class Fud61Prop(Enum):
    CMD = "CMD"  # command (former "COM")
    SW = "SW"  # Switching command ON/OFF [0=OFF, 1=ON] (offset=31 size=1)

    EDIM = "EDIM"  # Dimming value (absolute [0...255] or relative [0...100]) (offset=8, size=8 unit=%)
    EDIMR = "EDIMR"  # Dimming Range (offset=29, size=1)
    RMP = "RMP"  # Ramping time in seconds, 0 = no ramping, 1...255 = seconds to 100% (offset=16, size=8, unit=s)
    STR = "STR"  # Store final value (offset=30, No==0, Yes=1)


class Fud61Action:

    def __init__(self,
                 command: Fud61Command = None,
                 learn=False,
                 switch_state: SwitchState = None,
                 dim_state: int = None,
                 sender: int = None,
                 destination: int = None,
                 rssi: int = None
                 ):
        self.command = command
        self.learn = learn
        self.switch_state = switch_state
        self.dim_state = dim_state

        self.sender = sender
        self.destination = destination
        self.rssi = rssi

    def __str__(self):
        parts = []
        if self.command is not None:
            parts.append("command={}".format(self.command.name))
        if self.learn:
            parts.append("learn!")
        if self.switch_state is not None:
            parts.append("switch_state={}".format(self.switch_state))
        if self.dim_state is not None:
            parts.append("dim_state={}".format(self.dim_state))

        if parts:
            return ",".join(parts)
        else:
            return "<empty>"

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))


class Fud61Eep:
    """
    Handles conversions for EEP A5-38-08 command 0 + 2 (status request + dimming)

    Teach-in telegram BD3..DB0 must look like this: 0xE0, 0x40, 0x0D, 0x80
    | RORG | Data                        | Sender                      | Status   |
    | [a5] | [DB-3] [DB-2] [DB-1] [DB-0] | [ID-3] [ID-2] [ID-1] [ID-0] | [1 Byte] |
    |      |  0xE0   0x40   0x0D   0x80  |                             |          |

    See: https://www.eltako.com/fileadmin/downloads/de/Gesamtkatalog/Eltako_Gesamtkatalog_KapT_low_res.pdf
    """

    EEP = Eep(
        rorg=0xa5,
        func=0x38,
        type=0x08,
        direction=None,
        command=0x00
    )

    DEFAULT_DIM_STATE = 75

    DEFAULT_DIM_SPEED = 8

    @classmethod
    def create_packet(cls, action: Fud61Action) -> RadioPacket:
        _, packet = cls.create_props_and_packet(action)
        return packet

    @classmethod
    def create_props_and_packet(cls, action: Fud61Action) -> RadioPacket:
        eep = cls.EEP.clone()
        eep.command = action.command.value
        props = cls.create_props(action)

        packet = EnoceanPacketFactory.create_packet(
            eep=eep, destination=action.destination, sender=action.sender, learn=action.learn, **props
        )

        if action.learn:
            packet.data[1] = 0xE0  # see above
            packet.data[2] = 0x40
            packet.data[3] = 0x0D
            packet.data[4] = 0x80

        return props, packet

    @classmethod
    def create_props(cls, action: Fud61Action) -> Dict:
        if action.learn and cls:
            # dummy props
            props = {
                Fud61Prop.CMD.value: Fud61Command.DIMMING.value,
                Fud61Prop.SW.value: 1
            }
        elif action.command == Fud61Command.STATUS_REQUEST:
            props = cls.get_props_for_status_request()
        elif action.command == Fud61Command.DIMMING:
            props = cls.get_props_for_dim(action)
        else:
            raise ValueError("wrong A5-38-08 command!")

        return props

    @classmethod
    def extract_packet(cls, packet: RadioPacket, command: Optional[Fud61Command] = None) -> Fud61Action:
        props = cls.get_props_from_packet(packet, command)
        action = cls.get_action_from_props(props)
        return action

    @classmethod
    def get_props_for_status_request(cls):
        return {
            Fud61Prop.CMD.value: Fud61Command.STATUS_REQUEST.value,
        }

    @classmethod
    def get_props_for_dim(cls, action):
        # SW = "SW"  # Switching command ON/OFF [0=OFF, 1=ON] (offset=31 size=1)
        # EDIM = "EDIM"  # Dimming value (absolute [0...255] or relative [0...100]) (offset=8, size=8 unit=%)
        # EDIMR = "EDIMR"  # Dimming Range (offset=29, size=1)
        # RMP = "RMP"  # Ramping time in seconds, 0 = no ramping, 1...255 = seconds to 100% (offset=16, size=8, unit=s)
        # STR = "STR"  # Store final value (offset=30, No==0, Yes=1)

        action = copy.deepcopy(action)

        store_final_value = 0 if action.dim_state is None else 1

        # handle switch state
        if action.switch_state is None and action.dim_state is not None:
            action.switch_state = SwitchState.ON if action.dim_state else SwitchState.ON
        if action.switch_state not in [SwitchState.ON, SwitchState.OFF]:
            raise ValueError("invalid switch_state!")

        # handle dim state
        if action.dim_state is None:
            action.dim_state = 0 if action.switch_state == SwitchState.OFF else cls.DEFAULT_DIM_STATE

        # is consistent
        if (action.switch_state == SwitchState.ON) != (action.dim_state > 0):
            raise ValueError("invalid dim_state/switch_state combination!")

        props = {
            Fud61Prop.CMD.value: Fud61Command.DIMMING.value,
            Fud61Prop.RMP.value: cls.DEFAULT_DIM_SPEED,

            Fud61Prop.EDIM.value: action.dim_state,
            Fud61Prop.EDIMR.value: 0,
            Fud61Prop.STR.value: store_final_value,

            Fud61Prop.SW.value: 1 if action.switch_state == SwitchState.ON else 0,
        }

        return props

    @classmethod
    def can_read_packet(cls, packet) -> bool:
        return packet.packet_type == PACKET.RADIO and packet.rorg == cls.EEP.rorg

    @classmethod
    def get_props_from_packet(cls, packet: RadioPacket, command: Optional[Fud61Command] = None) -> Dict[str, int]:
        eep = cls.EEP.clone()

        if packet.packet_type == PACKET.RADIO and packet.rorg == eep.rorg:
            if command is None:
                eep.command = 0
                try:
                    tmp_props = EnoceanTools.extract_props(packet=packet, eep=eep)
                    eep.command = tmp_props[Fud61Prop.CMD.value]
                except AttributeError as ex:
                    raise EepPropException(ex)
            else:
                eep.command = command.value

            try:
                props = EnoceanTools.extract_props(packet=packet, eep=eep)
            except AttributeError as ex:
                raise EepPropException(ex)
        else:
            props = {}

        return props

    @classmethod
    def get_action_from_props(cls, props: Dict[str, int]) -> Fud61Action:
        action = Fud61Action()

        prop = props.get(Fud61Prop.CMD.value)
        for command in Fud61Command:
            if prop == command.value:
                action.command = command
                break

        if action.command == Fud61Command.DIMMING:
            prop = props.get(Fud61Prop.SW.value)
            if prop == 0:
                action.switch_state = SwitchState.OFF
            elif prop == 1:
                action.switch_state = SwitchState.ON
            else:
                action.switch_state = SwitchState.ERROR

            edim = props.get(Fud61Prop.EDIM.value)
            edimr = props.get(Fud61Prop.EDIMR.value)
            action.dim_state = cls.extract_dim_value(edim, edimr)

        else:
            action.switch_state = SwitchState.ERROR

        return action

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
