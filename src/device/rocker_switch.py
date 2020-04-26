import json
from enum import IntEnum
from typing import Optional, Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket, Packet

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.base_mqtt import BaseMqtt
from src.device.conf_device_key import ConfDeviceKey
from src.enocean_connector import EnoceanMessage
from src.enocean_packet_factory import EnoceanPacketFactory


class RockerAction(IntEnum):
    RELEASE = 0
    PRESS_SHORT = 1
    PRESS_LONG = 2


class RockerButton(IntEnum):
    """
    button ids to location: <above>
        [1] [3]
        [0] [2]
    work together as direction switch: 0 with 1; 2 with 3
    """
    ROCK0 = 0  # usually OFF (left side)
    ROCK1 = 1  # usually ON (left side)
    ROCK2 = 2  # usually OFF (right side)
    ROCK3 = 3  # usually ON (right side)


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

        self._mqtt_button_channels = []

    def set_config(self, config):
        BaseDevice.set_config(self, config)
        BaseMqtt.set_config(self, config)

        keys = [
            ConfDeviceKey.MQTT_CHANNEL_BUTTON_0, ConfDeviceKey.MQTT_CHANNEL_BUTTON_1,
            ConfDeviceKey.MQTT_CHANNEL_BUTTON_2, ConfDeviceKey.MQTT_CHANNEL_BUTTON_3
        ]
        for key in keys:
            self._mqtt_button_channels.append(Config.get_str(config, key))

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            return

        try:
            data = self._extract_packet(message.payload)
            self._logger.debug('process_mqtt_message: "%s"', data)

            message = json.dumps(data)
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
            r2 = 2 if action == RockerAction.PRESS_LONG else 0
            props = {'R1': button.value, 'EB': 1, 'R2': r2, 'SA': 0, 'T21': 1, 'NU': 1}

        return props

    @classmethod
    def simu_packet(cls, action: RockerAction, button: Optional[RockerButton],
                    rorg: Optional[int] = None, func: Optional[int] = None, type: Optional[int] = None,
                    destination: Optional[int] = None, sender: Optional[int] = None,
                    learn=False) -> RadioPacket:
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

        packet = EnoceanPacketFactory.create_radio_packet(
            rorg=rorg,
            rorg_func=func,
            rorg_type=type,
            destination=destination,
            sender=sender,
            learn=learn,
            **props
        )

        return packet

    def process_mqtt_message(self, message):
        """no message will be procressed!"""
