import json
from collections import namedtuple
from enum import Enum

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet, RadioPacket

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.base_mqtt import BaseMqtt
from src.device.conf_device_key import ConfDeviceKey
from src.eep import Eep
from src.enocean_connector import EnoceanMessage
from src.tools.rocker_switch_tools import RockerSwitchTools, RockerPress


class _OutputAttributes(Enum):
    TIMESTAMP = "TIMESTAMP"
    STATE = "STATE"
    BUTTON = "BUTTON"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


_MessageData = namedtuple("_MessageData", ["channel", "state", "button"])


class RockerSwitch(BaseDevice, BaseMqtt):

    DEFAULT_EEP = Eep(
        rorg=0xf6,
        func=0x02,
        type=0x02,
        direction=None,
        command=None
    )

    EMPTY_PROPS = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)

        self._eep = self.DEFAULT_EEP.clone()

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

        message_data = self._prepare_message_data(packet)
        if self.is_valid_channel(message_data.channel):
            mqtt_message = self._create_mqtt_message(message_data)
            self._publish_mqtt(mqtt_message, message_data.channel)

    def _prepare_message_data(self, packet: RadioPacket) -> _MessageData:
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 1, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}"

        try:
            action = RockerSwitchTools.extract_action_from_packet(packet)
            button = action.button.value if action.button is not None else None

            if action.press == RockerPress.PRESS_LONG:
                # search "long" first, then "short==standard", then "generic default"
                channel = self._mqtt_channels_long.get(button) or self._mqtt_channels.get(button) \
                          or self._mqtt_channel_state
            elif action.press == RockerPress.PRESS_SHORT:
                channel = self._mqtt_channels.get(button) or self._mqtt_channel_state
            elif action.press == RockerPress.RELEASE:
                channel = self._mqtt_channels.get(None) or self._mqtt_channel_state
            else:
                raise ValueError("unknown rocker press action!")

            return _MessageData(channel=channel, state=action.press.value, button=button)

        except (AttributeError, ValueError) as ex:  # TODO handle index errors
            self._logger.error("cannot evaluate data!")
            self._logger.exception(ex)
            return _MessageData(channel=self._mqtt_channel_state, state="ERROR", button=None)

    def _create_mqtt_message(self, message_data: _MessageData):
        data = {
            _OutputAttributes.STATE.value: message_data.state,
            _OutputAttributes.BUTTON.value: message_data.button,  # type: int
            _OutputAttributes.TIMESTAMP.value: self._now().isoformat()
        }

        json_text = json.dumps(data)
        return json_text

    def process_mqtt_message(self, message):
        """no message will be procressed!"""
