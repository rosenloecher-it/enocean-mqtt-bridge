import logging
from collections import namedtuple
from typing import Optional, Dict, Union

from src.mqtt_connector import MqttConnector
from src.tools.json_tools import JsonTools

_logger = logging.getLogger(__name__)


LastWill = namedtuple("LastWill", ["channel", "message", "qos", "retain"])


class MqttPublisher:

    def __init__(self):
        self._mqtt: Optional[MqttConnector] = None
        self.stored_last_wills = []

    def open(self, mqtt: MqttConnector):
        self._mqtt = mqtt

    def close(self):
        self._mqtt = None

    def publish(self, channel: str, payload: Union[str, Dict], qos: int = 0, retain: bool = False):
        if isinstance(payload, dict):
            payload = JsonTools.dumps(payload)

        if self._mqtt:
            self._mqtt.publish(
                channel=channel,
                payload=payload,
                qos=qos,
                retain=retain
            )
        else:
            _logger.warning("MqttConnector not set! Message is not send: %s=%s", channel, payload)

    def store_last_will(self, channel: str, message: str, qos: int = 0, retain: bool = False):
        self.stored_last_wills.append(LastWill(
            channel=channel,
            message=message,
            qos=qos,
            retain=retain
        ))

    def export_stored_last_wills(self):
        stored_last_wills = self.stored_last_wills
        self.stored_last_wills = []
        return stored_last_wills
