from enum import IntEnum
from typing import Dict, Optional, Union

import attr

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket
from src.common.eep import Eep
from src.common.eep_prop_exception import EepPropException
from src.enocean_packet_factory import EnoceanPacketFactory
from src.tools.enocean_tools import EnoceanTools


@attr.s
class _Fsb61BaseAction:

    time: Optional[Union[float, int]] = attr.ib(default=None)  # time in seconds

    destination: Optional[int] = attr.ib(default=None)
    sender: Optional[int] = attr.ib(default=None)
    rssi: Optional[int] = attr.ib(default=None)


class Fsb61CommandType(IntEnum):
    STOP = 0
    OPEN = 1
    CLOSE = 2
    STATUS_REQUEST = 3

    LEARN = 0x100

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))


@attr.s
class Fsb61Command(_Fsb61BaseAction):

    type: Optional[Fsb61CommandType] = attr.ib(default=None)

    @property
    def is_learn(self) -> bool:
        return self.type == Fsb61CommandType.LEARN


class Fsb61CommandConverter:

    _EEP = Eep(rorg=0xA5, func=0x3F, type=0x7F)

    _LEARN1 = 0xFF
    _LEARN2 = 0xF8
    _LEARN3 = 0x0D
    _LEARN4 = 0x80

    @classmethod
    def create_packet(cls, action: Fsb61Command) -> RadioPacket:
        _, packet = cls.create_props_and_packet(action)
        return packet

    @classmethod
    def create_props_and_packet(cls, action: Fsb61Command) -> (RadioPacket, dict):
        props = cls.create_props(action)

        packet = EnoceanPacketFactory.create_packet(
            eep=cls._EEP,
            destination=action.destination,
            sender=action.sender,
            **props
        )

        if action.is_learn:
            # 0xFFF80D80
            packet.data[1] = cls._LEARN1
            packet.data[2] = cls._LEARN2
            packet.data[3] = cls._LEARN3
            packet.data[4] = cls._LEARN4

        return props, packet

    @classmethod
    def create_props(cls, action: Fsb61Command) -> Dict:
        ct = Fsb61CommandType

        if action.type not in [ct.LEARN.value, ct.STOP.value, ct.OPEN.value, ct.CLOSE.value, ct.STATUS_REQUEST.value]:
            raise ValueError("Invalid command action!")

        props = {
            "CMD": action.type.value if action.type != ct.LEARN else ct.STOP.value,
            "DB0.0": 0,
            "DB0.1": 1,
            "DB0.7": 0,
            "LCK": 0,
            "LNRB": 0 if action.type == ct.LEARN else 1,
        }

        if action.type in [ct.OPEN, ct.CLOSE]:
            if action.time is None:
                raise ValueError("Missing time!")

            time_value = int(action.time * 10)
            if time_value > 3000 or time_value < 0:
                raise ValueError("Invalid time value ({})!".format(action.time))

            props["MSB"] = (time_value >> 8) & 0xFF
            props["LSB"] = time_value & 0xFF

        return props

    @classmethod
    def is_command_packet(cls, packet: RadioPacket) -> bool:
        return packet.rorg == cls._EEP.rorg

    @classmethod
    def extract_packet(cls, packet: RadioPacket) -> Fsb61Command:
        ct = Fsb61CommandType
        action = Fsb61Command()

        if packet.data[1] == cls._LEARN1 and packet.data[2] == cls._LEARN2 and packet.data[3] == cls._LEARN3 \
                and packet.data[4] == cls._LEARN4:
            action.type = ct.LEARN
            return action

        props = cls.get_props_from_packet(packet)

        action.sender = packet.sender_int
        action.rssi = packet.dBm

        cmd_value = props["CMD"]
        command_types = [ct.STOP, ct.OPEN, ct.CLOSE, ct.STATUS_REQUEST]
        for command_type in command_types:
            if command_type.value == cmd_value:
                action.type = command_type
                break

        if action.type in [ct.OPEN, ct.CLOSE]:
            msb = props["MSB"]
            lsb = props["LSB"]
            action.time = ((msb << 8) + lsb) / 10

        return action

    @classmethod
    def get_props_from_packet(cls, packet: RadioPacket) -> Dict[str, int]:
        eep = cls._EEP

        if packet.packet_type == PACKET.RADIO and packet.rorg == eep.rorg:
            try:
                props = EnoceanTools.extract_props(packet=packet, eep=eep)
            except AttributeError as ex:
                raise EepPropException(ex)
        else:
            props = {}

        return props


class Fsb61StateType(IntEnum):
    UNKNOWN = 0

    OPENED = 1  # just stopped, but drove x seconds
    CLOSED = 2  # just stopped, but drove x seconds

    OPENING = 3  # started moving, no new position yet
    CLOSING = 4  # started moving, no new position yet

    STOPPED = 5  # signaled when the shutter stops at the device (hardware) time setting => interpreted via last OPENING, CLOSING

    POSITION = 6  # re-interpretet STOPPED as 0% or 100% (via prio OPENING, CLOSING)

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))


@attr.s
class Fsb61State(_Fsb61BaseAction):
    type: Optional[Fsb61StateType] = attr.ib(default=None)

    position: Optional[int] = attr.ib(default=None)


class Fsb61StateConverter:

    _EEP = Eep(rorg=0xF6, func=0x02, type=0x02)

    @classmethod
    def extract_packet(cls, packet: RadioPacket) -> Fsb61State:

        status = Fsb61State()

        status.rssi = packet.dBm

        status.sender = packet.sender_int
        status.destination = packet.destination_int

        if Fsb61CommandConverter.is_command_packet(packet):  # packet.rorg == 0xa5
            command = Fsb61CommandConverter.extract_packet(packet)
            if command.type == Fsb61CommandType.CLOSE:
                status.type = Fsb61StateType.CLOSED
                status.time = command.time
            elif command.type == Fsb61CommandType.OPEN:
                status.type = Fsb61StateType.OPENED
                status.time = command.time
            elif command.type == Fsb61CommandType.STOP:
                status.type = Fsb61StateType.STOPPED
                status.time = 0
            else:
                raise EepPropException("Invalid command type!")

        elif packet.rorg == cls._EEP.rorg:
            props = EnoceanTools.extract_props(packet, cls._EEP)
            r2 = props["R2"]  # R2 (Rocker 2nd action)
            sa = props["SA"]  # 2nd action valid
            if sa == 1:
                if r2 == 0:  # 0: Button AI: "Switch light on" or "Dim light up" or "Move blind open"
                    status.type = Fsb61StateType.OPENING
                elif r2 == 1:  # 1: Button A0: "switch light off" or "Dim light down" or "Move blind closed"
                    status.type = Fsb61StateType.CLOSING

            elif sa == 0:
                if r2 == 1:  # 1: Button A0: "switch light off" or "Dim light down" or "Move blind closed"
                    status.type = Fsb61StateType.CLOSING
                else:
                    status.type = Fsb61StateType.STOPPED

            if status.type is None:
                raise EepPropException("Invalid data ({})!".format(props))

        else:
            status.type = Fsb61StateType.UNKNOWN

        return status

    @classmethod
    def create_packet(cls, status: Fsb61State) -> Optional[RadioPacket]:
        """needed for test only, so not complete!"""
        if status.type in [Fsb61StateType.CLOSING, Fsb61StateType.OPENING, Fsb61StateType.STOPPED]:
            if status.type == Fsb61StateType.CLOSING:
                r2 = 1
                sa = 1
            elif status.type == Fsb61StateType.OPENING:
                r2 = 0
                sa = 1
            elif status.type == Fsb61StateType.STOPPED:
                r2 = 0
                sa = 0
            else:
                raise EepPropException("Wrong Fsb61StateType  ({})!".format(status.type))

            props = {'R1': 0, 'EB': 0, 'R2': r2, 'SA': sa, 'T21': 1, 'NU': 1}

            packet = EnoceanPacketFactory.create_packet(
                eep=cls._EEP, destination=status.destination, sender=status.sender, learn=False, **props
            )
            packet.dBm = status.rssi
            return packet
        else:
            return None
