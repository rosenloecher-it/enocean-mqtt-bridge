from enum import IntEnum, Enum
from typing import Dict, Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket


from src.common.eep import Eep
from src.common.switch_status import SwitchStatus
from src.enocean_packet_factory import EnoceanPacketFactory
from src.common.eep_prop_exception import EepPropException
from src.tools.enocean_tools import EnoceanTools


class Fsr61Command(IntEnum):
    STATUS_REQUEST = 0
    SWITCHING = 1


class Fsr61Prop(Enum):
    # common
    CMD = "CMD"  # command
    SW = "SW"  # Switching command ON/OFF [0=OFF, 1=ON] (offset=31 size=1)

    # switch
    DEL = "DEL"  # 0 = Duration (switch immediately...) 1 = Delay (offset=30, size=1)
    LCK = "LCK"  # Lock for duration time (if >0), unlimited time of no time [Unlock=0, Lock=1] (offset=29, size=1)
    TIM = "TIM"  # Time in 1/10 seconds. 0 = no time specifed (offset=8, size=16, unit=s)


class Fsr61Action:

    def __init__(self,
                 command: Fsr61Command = Fsr61Command.STATUS_REQUEST,
                 learn=False,
                 switch_state: SwitchStatus = None,
                 sender: int = None,
                 destination: int = None
                 ):
        self.command = command
        self.learn = learn
        self.switch_state = switch_state

        self.sender = sender
        self.destination = destination

    def __str__(self):
        parts = []
        if self.command is not None:
            parts.append("command={}".format(self.command.name))
        if self.learn:
            parts.append("learn!")
        if self.switch_state is not None:
            parts.append("switch_state={}".format(self.switch_state))

        if parts:
            return ",".join(parts)
        else:
            return "<empty>"

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))


class Fsr61Eep:
    """
    Handles conversions for EEP A5-38-08 command 0 + 1 (status request + switching)
    """

    EEP = Eep(
        rorg=0xa5,
        func=0x38,
        type=0x08,
        direction=None,
        command=0x00
    )

    @classmethod
    def create_packet(cls, action: Fsr61Action) -> RadioPacket:
        _, packet = cls.create_props_and_packet(action)
        return packet

    @classmethod
    def create_props_and_packet(cls, action: Fsr61Action) -> RadioPacket:
        eep = cls.EEP.clone()
        # command is to be set as "COM"
        eep.command = action.command.value
        if action.command == Fsr61Command.STATUS_REQUEST:
            props = cls.get_props_for_status_request()
            # eep.command = 0
        elif action.command == Fsr61Command.SWITCHING:
            props = cls.get_props_for_switch(action)
        else:
            raise ValueError("wrong A5-38-08 command!")

        packet = EnoceanPacketFactory.create_packet(
            eep=eep, destination=action.destination, sender=action.sender, learn=action.learn, **props
        )
        return props, packet

    @classmethod
    def extract_packet(cls, packet: RadioPacket, command: Optional[Fsr61Command] = None) -> Fsr61Action:
        props = cls.get_props_from_packet(packet, command)
        action = cls.get_action_from_props(props)
        return action

    @classmethod
    def get_props_for_status_request(cls):
        return {
            Fsr61Prop.CMD.value: Fsr61Command.STATUS_REQUEST.value,
        }

    @classmethod
    def get_props_for_switch(cls, action: Fsr61Action):
        # SW   0: OFF, 1: ON
        props = {
            Fsr61Prop.CMD.value: Fsr61Command.SWITCHING.value,
        }
        if action.switch_state == SwitchStatus.ON:
            props[Fsr61Prop.SW.value] = 1
        elif action.switch_state == SwitchStatus.OFF:
            props[Fsr61Prop.SW.value] = 0
        else:
            raise ValueError("Wrong SwitchState!")
        return props

    @classmethod
    def can_read_packet(cls, packet) -> bool:
        return packet.packet_type == PACKET.RADIO and packet.rorg == cls.EEP.rorg

    @classmethod
    def get_props_from_packet(cls, packet, command: Optional[Fsr61Command] = None) -> Dict[str, int]:
        eep = cls.EEP.clone()

        if packet.packet_type == PACKET.RADIO and packet.rorg == eep.rorg:
            if command is None:
                eep.command = 0
                try:
                    tmp_props = EnoceanTools.extract_props(packet=packet, eep=eep)
                    eep.command = tmp_props[Fsr61Prop.CMD.value]
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
    def get_action_from_props(cls, props: Dict[str, int]) -> Fsr61Action:
        # COM  0x01: Switching, 0x00: Status Request (*)
        # SW   0: OFF, 1: ON

        action = Fsr61Action()

        prop = props.get(Fsr61Prop.CMD.value)
        for command in Fsr61Command:
            if prop == command.value:
                action.command = command
                break

        if action.command == Fsr61Command.SWITCHING:
            prop = props.get(Fsr61Prop.SW.value)
            if prop == 0:
                action.switch_state = SwitchStatus.OFF
            elif prop == 1:
                action.switch_state = SwitchStatus.ON
            else:
                action.switch_state = SwitchStatus.ERROR

        return action
