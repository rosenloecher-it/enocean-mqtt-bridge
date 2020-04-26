from enum import IntEnum
from typing import Optional, Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket, Packet

from src.device.base_device import BaseDevice
from src.device.base_mqtt import BaseMqtt
from src.enocean_connector import EnoceanMessage
from src.enocean_packet_factory import EnoceanPacketFactory
from src.tools import Tools


class RockerAction(IntEnum):
    RELEASE = 0
    PRESS_SINGLE = 1
    PRESS_DOUBLE = 2


class RockerButton(IntEnum):
    """
    button ids to location: <above>
        [1] [3]
        [0] [2]
    work together as direction switvch:
        - 0 + 1
        - 2 + 3
    """
    ROCK11 = 1  # usually ON
    ROCK12 = 0  # usually OFF
    ROCK21 = 3  # usually ON
    ROCK22 = 2  # usually OFF


class RockerSwitch(BaseDevice, BaseMqtt):

    DEFAULT_ENOCEAN_RORG = 0xf6
    DEFAULT_ENOCEAN_FUNC = 0x02
    DEFAULT_ENOCEAN_TYPE = 0x02

    DEFAULT_ENOCEAN_DIRECTION = None
    DEFAULT_ENOCEAN_COMMAND = None

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)

        # default config values
        self._enocean_rorg = self.DEFAULT_ENOCEAN_RORG
        self._enocean_func = self.DEFAULT_ENOCEAN_FUNC
        self._enocean_type = self.DEFAULT_ENOCEAN_TYPE
        self._enocean_direction = self.DEFAULT_ENOCEAN_DIRECTION
        self._enocean_command = self.DEFAULT_ENOCEAN_COMMAND

    def set_config(self, config):
        BaseDevice.set_config(self, config)
        BaseMqtt.set_config(self, config)

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            return

        try:
            data = self._extract_packet(message.payload)
            self._logger.debug('process_mqtt_message: "%s"', data)

            # message = json.dumps(data)
        except Exception as ex:
            self._logger.exception(ex)

        # self._publish_mqtt(message)

    def _check_mqtt_settings(self):
        pass

    @classmethod
    def simu_packet_props(cls,
                          action: RockerAction,
                          button: Optional[RockerButton]) -> Dict[str, int]:
        """
        :param action: True == press, False == release button
        :param button: may None in case of release
        :return:
        """
        if action == RockerAction.RELEASE:
            props = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}
        else:
            if button is None:
                raise ValueError("no RockerSwitchButton defined!")
            r2 = 2 if action == RockerAction.PRESS_DOUBLE else 0
            props = {'R1': button.value, 'EB': 1, 'R2': r2, 'SA': 0, 'T21': 1, 'NU': 1}

        return props

    @classmethod
    def simu_packet(cls, action: RockerAction, button: Optional[RockerButton],
                    rorg: Optional[int] = None, func: Optional[int] = None, type: Optional[int] = None,
                    dest_id: Optional[int] = None) -> RadioPacket:
        """
        :param bool press: True == press, False == release button
        :param int button: range 0 - 3 for the 4 single buttons; may None in case of release
        :param rorg:
        :param func:
        :param type:
        :param dest_id:
        :return:
        """
        props = cls.simu_packet_props(action, button)

        rorg = rorg or cls.DEFAULT_ENOCEAN_RORG
        func = func or cls.DEFAULT_ENOCEAN_FUNC
        type = type or cls.DEFAULT_ENOCEAN_TYPE

        dest_id = dest_id or 0xffffffff
        dest_bytes = Tools.int_to_byte_list(dest_id, 4)

        # if action == SwitchAction.ON:
        #     props = {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        # elif action == SwitchAction.OFF:
        #     props = {'R1': 0, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        # elif action == SwitchAction.RELEASE:
        #     props = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}
        # else:
        #     raise RuntimeError()
        #
        # # could also be 0xffffffff
        # destination = Tools.int_to_byte_list(self._enocean_id, 4)
        #
        packet = EnoceanPacketFactory.create_radio_packet(
            rorg=rorg,
            rorg_func=func,
            rorg_type=type,
            destination=dest_bytes,
            learn=False,
            **props
        )

        return packet

    def process_mqtt_message(self, message):
        """no message will be procressed!"""
