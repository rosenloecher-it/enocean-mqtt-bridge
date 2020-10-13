import json
from collections import namedtuple
from enum import IntEnum, Enum
from typing import Optional, Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket, Packet

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.base_mqtt import BaseMqtt
from src.device.conf_device_key import ConfDeviceKey
from src.eep import Eep
from src.enocean_connector import EnoceanMessage
from src.enocean_packet_factory import EnoceanPacketFactory


class RockerAction(Enum):
    RELEASE = "RELEASE"
    PRESS_SHORT = "SHORT"  # presset
    PRESS_LONG = "LONG"  # pressed
    ERROR = "ERROR"


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


class _OutputAttributes(Enum):
    TIMESTAMP = "TIMESTAMP"
    STATE = "STATE"
    BUTTON = "BUTTON"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


_MessageData = namedtuple("_MessageData", ["channel", "button", "action"])


class RockerSwitch(BaseDevice, BaseMqtt):

    DEFAULT_ENOCEAN_RORG = 0xf6
    DEFAULT_ENOCEAN_FUNC = 0x02
    DEFAULT_ENOCEAN_TYPE = 0x02

    DEFAULT_ENOCEAN_DIRECTION = None
    DEFAULT_ENOCEAN_COMMAND = None

    EMPTY_PROPS = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)

        self._eep = Eep(
            rorg=self.DEFAULT_ENOCEAN_RORG,
            func=self.DEFAULT_ENOCEAN_FUNC,
            type=self.DEFAULT_ENOCEAN_TYPE,
            direction=self.DEFAULT_ENOCEAN_DIRECTION,
            command=self.DEFAULT_ENOCEAN_COMMAND
        )

        self._mqtt_channels = {}
        self._mqtt_channels_long = {}

    def set_config(self, config):
        BaseDevice.set_config(self, config)
        BaseMqtt._set_config(self, config)

        items = [
            (ConfDeviceKey.MQTT_CHANNEL_BTN_LONG_0, 0),
            (ConfDeviceKey.MQTT_CHANNEL_BTN_LONG_1, 1),
            (ConfDeviceKey.MQTT_CHANNEL_BTN_LONG_2, 2),
            (ConfDeviceKey.MQTT_CHANNEL_BTN_LONG_3, 3),
        ]
        for key, index in items:
            channel = Config.get_str(config, key)
            if channel:
                self._mqtt_channels_long[index] = channel

        items = [
            (ConfDeviceKey.MQTT_CHANNEL_BTN_0, 0),
            (ConfDeviceKey.MQTT_CHANNEL_BTN_1, 1),
            (ConfDeviceKey.MQTT_CHANNEL_BTN_2, 2),
            (ConfDeviceKey.MQTT_CHANNEL_BTN_3, 3),
            (ConfDeviceKey.MQTT_CHANNEL_RELEASE, None),
        ]
        for key, index in items:
            channel = Config.get_str(config, key)
            if channel:
                self._mqtt_channels[index] = channel

    @classmethod
    def is_valid_channel(cls, channel):
        return channel and channel not in ["~", "-"]

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            return

        packet_data = self._extract_packet(message.payload)
        self._logger.debug('process_mqtt_message: "%s"', packet_data)
        message_data = self._prepare_message_data(packet_data)

        if self.is_valid_channel(message_data.channel):
            mqtt_message = self._create_mqtt_message(message_data)
            self._publish_mqtt(mqtt_message, message_data.channel)

    def _prepare_message_data(self, data) -> _MessageData:
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 1, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}"

        try:
            if data["SA"] == 1:
                index = data["R2"]
                channel = self._mqtt_channels_long.get(index) or self._mqtt_channels.get(index) \
                          or self._mqtt_channel_state
                return _MessageData(channel=channel, button=index, action=RockerAction.PRESS_LONG)
            elif data["EB"] == 1:
                index = data["R1"]
                channel = self._mqtt_channels.get(index) or self._mqtt_channel_state
                return _MessageData(channel=channel, button=index, action=RockerAction.PRESS_SHORT)
            elif data == self.EMPTY_PROPS:
                channel = self._mqtt_channels.get(None) or self._mqtt_channel_state
                return _MessageData(channel=channel, button=None, action=RockerAction.RELEASE)
            else:
                return _MessageData(channel=self._mqtt_channel_state, button=None, action=RockerAction.ERROR)

        except AttributeError as ex:  # TODO handle index errors
            self._logger.error("cannot evaluate data: %s (%s)", data, ex)
            return _MessageData(channel=self._mqtt_channel_state, button=None, action=RockerAction.ERROR)

    def _create_mqtt_message(self, message_data: _MessageData):
        data = {
            _OutputAttributes.STATE.value: message_data.action.value,
            _OutputAttributes.BUTTON.value: message_data.button,  # type: int
            _OutputAttributes.TIMESTAMP.value: self._now().isoformat()
        }

        json_text = json.dumps(data)
        return json_text

    @classmethod
    def simu_packet_props(cls,
                          action: RockerAction,
                          button: Optional[RockerButton]) -> Dict[str, int]:
        """
        :param action: True == press, False == release button
        :param button: may None in case of release
        :return:
        """
        if action in [RockerAction.PRESS_SHORT, RockerAction.PRESS_LONG]:
            if button is None:
                raise ValueError("no RockerSwitchButton defined!")
            if action == RockerAction.PRESS_LONG:
                props = {'R1': 0, 'EB': 0, 'R2': button.value, 'SA': 1, 'T21': 1, 'NU': 1}
            else:  # short
                props = {'R1': button.value, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        elif action == RockerAction.RELEASE:
            props = cls.EMPTY_PROPS
        else:
            raise ValueError()

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
