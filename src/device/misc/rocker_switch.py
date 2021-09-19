import json
from collections import namedtuple

from enocean.protocol.packet import RadioPacket

from src.config import Config
from src.common.json_attributes import JsonAttributes
from src.device.base.base_enocean import BaseEnocean
from src.device.base.base_mqtt import BaseMqtt
from src.common.conf_device_key import ConfDeviceKey
from src.enocean_connector import EnoceanMessage
from src.device.misc.rocker_switch_tools import RockerSwitchTools, RockerPress


_MessageData = namedtuple("_MessageData", ["channel", "state", "button"])


class RockerSwitch(BaseEnocean, BaseMqtt):

    def __init__(self, name):
        BaseEnocean.__init__(self, name)
        BaseMqtt.__init__(self)

        self._eep = RockerSwitchTools.DEFAULT_EEP.clone()

        self._mqtt_channels = {}
        self._mqtt_channels_long = {}

    def set_config(self, config):
        BaseEnocean.set_config(self, config)
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
        packet = self._extract_default_radio_packet(message)
        if not packet:
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
            JsonAttributes.STATE: message_data.state,
            JsonAttributes.BUTTON: message_data.button,  # type: int
            JsonAttributes.TIMESTAMP: self._now().isoformat()
        }

        json_text = json.dumps(data)
        return json_text

    def process_mqtt_message(self, message):
        """no message will be procressed!"""
