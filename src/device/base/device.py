import abc
import copy
import datetime
import json
import logging
from threading import Timer
from typing import Optional, Dict, Union

from jsonschema import validate, ValidationError
from paho.mqtt.client import MQTTMessage

from src.common.json_attributes import JsonAttributes
from src.common.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.mqtt_publisher import MqttPublisher
from src.tools.time_tools import TimeTools

_class_logger = logging.getLogger(__name__)


CONFKEY_ENOCEAN_SENDER = "enocean_sender"
CONFKEY_ENOCEAN_TARGET = "enocean_target"
CONFKEY_LOG_SENT_PACKETS = "log_sent_packets"

CONFKEY_MQTT_CHANNEL_CMD = "mqtt_channel_cmd"
CONFKEY_MQTT_CHANNEL_STATE = "mqtt_channel_state"
CONFKEY_MQTT_LAST_WILL = "mqtt_last_will"
CONFKEY_MQTT_QOS = "mqtt_quality"
CONFKEY_MQTT_RETAIN = "mqtt_retain"
CONFKEY_MQTT_TIME_OFFLINE = "mqtt_time_offline"


DEVICE_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_ENOCEAN_SENDER: {"type": "integer"},
        CONFKEY_ENOCEAN_TARGET: {"type": "integer"},
        CONFKEY_LOG_SENT_PACKETS: {"type": "boolean"},

        CONFKEY_MQTT_CHANNEL_CMD: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_CHANNEL_STATE: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_LAST_WILL: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_QOS: {"type": "integer", "enum": [0, 1, 2]},
        CONFKEY_MQTT_RETAIN: {"type": "boolean"},
        CONFKEY_MQTT_TIME_OFFLINE: {"type": "number", "description": "time in seconds after which the device gets announced as offline."},
    },
    "required": [
        CONFKEY_ENOCEAN_SENDER,
        CONFKEY_ENOCEAN_TARGET,
        CONFKEY_MQTT_CHANNEL_STATE,
        CONFKEY_MQTT_CHANNEL_CMD,
    ],
}


class Device:
    """Encapsulates Enocean and MQTT basics."""

    DEFAULT_MQTT_QOS = 2
    DEFAULT_MQTT_PORT = 1883
    DEFAULT_MQTT_PORT_SSL = 1883
    DEFAULT_MQTT_PROTOCOL = 4  # 5==MQTTv5, default: 4==MQTTv311, 3==MQTTv31

    OFFLINE_REFRESH_TIME = 900  # in seconds

    def __init__(self, name: str):
        if not name:
            raise RuntimeError("Device name required!")
        self._name = name
        self._logger_by_name: Optional[logging.Logger] = None

        self._log_sent_packets = False
        self._enocean_connector = None

        self._enocean_target: Optional[int] = None
        self._enocean_sender: Optional[int] = None  # to distinguish between different actors

        self._mqtt_channel_cmd: Optional[str] = None
        self._mqtt_channel_state: Optional[str] = None
        self._mqtt_last_will: Optional[str] = None
        self._mqtt_qos: Optional[int] = None
        self._mqtt_retain: Optional[bool] = None

        self._mqtt_time_offline: Optional[int] = None  # seconds
        self._last_refresh_time = self._now()
        self._last_will_sent_time: Optional[datetime] = None

        self._mqtt_publisher: Optional[MqttPublisher] = None

    @property
    def _logger(self):
        if self._logger_by_name:
            return self._logger_by_name

        if self._name:
            self._logger_by_name = logging.getLogger(self._name)
            return self._logger_by_name

        return _class_logger

    @property
    def name(self):
        return self._name

    def set_config(self, config):
        self._set_config(config, skip_require_fields=[])

    def _set_config(self, config, skip_require_fields: [str]):
        schema = self.filter_required_fields(DEVICE_JSONSCHEMA, skip_require_fields)
        self.validate_config(config, schema)

        self._enocean_target = config.get(CONFKEY_ENOCEAN_TARGET)
        self._enocean_sender = config.get(CONFKEY_ENOCEAN_SENDER)
        self._log_sent_packets = config.get(CONFKEY_LOG_SENT_PACKETS, False)

        self._mqtt_channel_cmd = config.get(CONFKEY_MQTT_CHANNEL_CMD)  # may be optional
        self._mqtt_channel_state = config.get(CONFKEY_MQTT_CHANNEL_STATE)  # may be optional
        self._mqtt_last_will = config.get(CONFKEY_MQTT_LAST_WILL)
        self._mqtt_qos = config.get(CONFKEY_MQTT_QOS, self.DEFAULT_MQTT_QOS)
        self._mqtt_retain = config.get(CONFKEY_MQTT_RETAIN, False)
        self._mqtt_time_offline = config.get(CONFKEY_MQTT_TIME_OFFLINE)

    @property
    def enocean_targets(self):
        return [self._enocean_target] if self._enocean_target else []

    def set_enocean_connector(self, enocean):
        self._enocean_connector = enocean

    def _send_enocean_packet(self, packet, delay=0):
        instance = self

        def do_send():
            try:
                packet.build()
                if self._log_sent_packets:
                    instance._logger.debug("packet is being sent: %s", packet)

                instance._enocean_connector.send(packet)
            except Exception as ex:
                instance._logger.exception(ex)

        if delay < 0.001:
            do_send()
        else:
            t = Timer(delay, do_send)
            t.start()

    @abc.abstractmethod
    def process_enocean_message(self, message: EnoceanMessage):
        raise NotImplementedError()

    def get_mqtt_last_will_channel(self):
        """signal ensor state, outbound channel"""
        return self._mqtt_channel_state

    def get_mqtt_channel_subscriptions(self):
        """outbound mqtt channels"""
        return [self._mqtt_channel_cmd] if self._mqtt_channel_cmd else []

    def set_mqtt_publisher(self, mqtt_publisher: MqttPublisher):
        self._mqtt_publisher = mqtt_publisher

    def open_mqtt(self):
        pass

    def close_mqtt(self):
        if self.mqtt_last_will:
            self._publish_mqtt(self.mqtt_last_will)
            self._logger.debug("last will sent: disconnecting")

    def _publish_mqtt(self, payload: Union[str, Dict], mqtt_channel: str = None):
        inner_mqtt_channel = mqtt_channel or self._mqtt_channel_state
        if inner_mqtt_channel:
            self._mqtt_publisher.publish(
                channel=inner_mqtt_channel,
                payload=payload,
                qos=self._mqtt_qos,
                retain=self._mqtt_retain
            )

    @abc.abstractmethod
    def process_mqtt_message(self, message: MQTTMessage):
        raise NotImplementedError

    def set_last_will(self):
        mqtt_last_will = self.mqtt_last_will
        if mqtt_last_will:
            self._mqtt_publisher.store_last_will(
                channel=self._mqtt_channel_state,
                message=mqtt_last_will,
                qos=self._mqtt_qos,
                retain=self._mqtt_retain
            )
            self._logger.info("mqtt last will: {0}={1}".format(self._mqtt_channel_state, self._mqtt_last_will))

    def _reset_offline_refresh_timer(self):
        self._last_refresh_time = self._now()
        self._last_will_sent_time = None

    def _check_and_send_offline(self):
        if self._is_offline:
            now = self._now()
            last_sent = (now - self._last_will_sent_time).total_seconds() if self._last_will_sent_time is not None else None
            if last_sent is None or last_sent >= self.OFFLINE_REFRESH_TIME:
                mqtt_last_will = self._mqtt_last_will
                if mqtt_last_will:
                    self._publish_mqtt(self._mqtt_last_will)
                    self._logger.info("last will sent: missing refresh")
                    self._last_will_sent_time = now

    @property
    def _is_offline(self):
        if self._mqtt_time_offline is None or self._mqtt_time_offline <= 0:
            return False
        now = self._now()
        diff = (now - self._last_refresh_time).total_seconds()
        return diff >= self._mqtt_time_offline

    @property
    def mqtt_last_will(self):
        if self._mqtt_last_will is not None:
            return self._mqtt_last_will
        return self._generated_mqtt_last_will

    @property
    def _generated_mqtt_last_will(self):
        data = {
            JsonAttributes.DEVICE: self.name,
            JsonAttributes.STATUS: "offline",
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
        }
        return json.dumps(data, sort_keys=True)

    @classmethod
    def filter_required_fields(cls, schema, skip_require_fields):
        schema = copy.deepcopy(schema)
        if skip_require_fields == ["*"]:
            del schema["required"]
        else:
            require_fields = schema.get("required")
            if require_fields:
                schema["required"] = list(filter(lambda f: f not in skip_require_fields, require_fields))
        return schema

    @classmethod
    def validate_config(cls, config, schema):
        try:
            validate(instance=config, schema=schema)
        except ValidationError as ex:
            raise DeviceException(ex)

    def _now(self):
        """overwrite in test to simulate different times"""
        return TimeTools.now()
