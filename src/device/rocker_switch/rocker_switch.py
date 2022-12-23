import attr
from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.device.base.device import CONFKEY_MQTT_CHANNEL_STATE, CONFKEY_MQTT_CHANNEL_CMD, Device, CONFKEY_ENOCEAN_SENDER
from src.common.device_exception import DeviceException
from src.device.rocker_switch.rocker_switch_tools import RockerSwitchTools, RockerPress
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools


CONFKEY_MQTT_CHANNEL_BTN_0 = "mqtt_channel_0"
CONFKEY_MQTT_CHANNEL_BTN_1 = "mqtt_channel_1"
CONFKEY_MQTT_CHANNEL_BTN_2 = "mqtt_channel_2"
CONFKEY_MQTT_CHANNEL_BTN_3 = "mqtt_channel_3"

CONFKEY_MQTT_CHANNEL_BTN_LONG_0 = "mqtt_channel_long_0"
CONFKEY_MQTT_CHANNEL_BTN_LONG_1 = "mqtt_channel_long_1"
CONFKEY_MQTT_CHANNEL_BTN_LONG_2 = "mqtt_channel_long_2"
CONFKEY_MQTT_CHANNEL_BTN_LONG_3 = "mqtt_channel_long_3"


ROCKER_COMMAND = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "minLength": 1,
            "description": "Command topic to which the message is sent."
        },
        "payload": {
            "type": "string",
            "minLength": 1,
            "description": "Payload to send."
        },
    },
    "description": "Configure a MQTT message, which is sent each key press.",
    "additionalProperties": False,
    "required": ["topic", "payload"]
}

ROCKER_SWITCH_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_MQTT_CHANNEL_BTN_0: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_1: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_2: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_3: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_LONG_0: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_LONG_1: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_LONG_2: ROCKER_COMMAND,
        CONFKEY_MQTT_CHANNEL_BTN_LONG_3: ROCKER_COMMAND,
    }
}


@attr.frozen
class _RockerCommand:
    topic = attr.ib()  # type: str
    payload = attr.ib()  # type: str


class RockerSwitch(Device):

    def __init__(self, name):
        super().__init__(name)

        self._eep = RockerSwitchTools.DEFAULT_EEP.clone()

        self._mqtt_channels = {}
        self._mqtt_channels_long = {}

    def _set_config(self, config, skip_require_fields: [str]):
        skip_require_fields = [*skip_require_fields, CONFKEY_MQTT_CHANNEL_CMD, CONFKEY_MQTT_CHANNEL_STATE, CONFKEY_ENOCEAN_SENDER]

        super()._set_config(config, skip_require_fields)

        schema = self.filter_required_fields(ROCKER_SWITCH_JSONSCHEMA, skip_require_fields)
        self.validate_config(config, schema)

        if self._mqtt_channel_state:
            raise DeviceException(f"'{CONFKEY_MQTT_CHANNEL_STATE}' is not used here. Set the command topic for each key separately!")

        items = [
            (CONFKEY_MQTT_CHANNEL_BTN_LONG_0, 0),
            (CONFKEY_MQTT_CHANNEL_BTN_LONG_1, 1),
            (CONFKEY_MQTT_CHANNEL_BTN_LONG_2, 2),
            (CONFKEY_MQTT_CHANNEL_BTN_LONG_3, 3),
        ]
        for key, index in items:
            data = config.get(key)
            if data:
                self._mqtt_channels_long[index] = _RockerCommand(**data)

        items = [
            (CONFKEY_MQTT_CHANNEL_BTN_0, 0),
            (CONFKEY_MQTT_CHANNEL_BTN_1, 1),
            (CONFKEY_MQTT_CHANNEL_BTN_2, 2),
            (CONFKEY_MQTT_CHANNEL_BTN_3, 3),
        ]
        for key, index in items:
            data = config.get(key)
            if data:
                self._mqtt_channels[index] = _RockerCommand(**data)

    @classmethod
    def is_valid_channel(cls, channel):
        return channel and channel not in ["~", "-"]

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: RadioPacket
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return
        if packet.rorg != self._eep.rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return

        message_data = self._find_rocker_command(packet)
        if message_data and message_data.topic:
            self._publish_mqtt(message_data.payload, message_data.topic)

    def _find_rocker_command(self, packet: RadioPacket) -> _RockerCommand:
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 1, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}"

        try:
            action = RockerSwitchTools.extract_action_from_packet(packet)
            button = action.button.value if action.button is not None else None

            if action.press == RockerPress.PRESS_LONG:
                # search "long" first, then "short==standard", then "generic default"
                rocker_command = self._mqtt_channels_long.get(button) or self._mqtt_channels.get(button)
            elif action.press == RockerPress.PRESS_SHORT:
                rocker_command = self._mqtt_channels.get(button) or self._mqtt_channel_state
            elif action.press == RockerPress.RELEASE:
                rocker_command = None  # don't send anything
            else:
                raise ValueError("unknown rocker press action!")

            return rocker_command

        except (AttributeError, ValueError) as ex:  # TODO handle index errors
            self._logger.error("cannot evaluate data!")
            self._logger.exception(ex)
            return _RockerCommand(channel=self._mqtt_channel_state, status="ERROR", button=None)

    def process_mqtt_message(self, message):
        """no message will be procressed!"""
