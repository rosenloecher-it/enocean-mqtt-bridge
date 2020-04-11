from collections import namedtuple

from src.mqtt_connector import MqttConnector

LastWill = namedtuple("LastWill", ["channel", "message", "qos", "retain"])


class MqttPublisher:

    def __init__(self):
        self._mqtt = None  # type: MqttConnector
        self.stored_last_wills = []

    def open(self, mqtt: MqttConnector):
        self._mqtt = mqtt

    def close(self):
        self._mqtt = None

    def publish(self, channel: str, message: str, qos: int = 0, retain: bool = False):
        if self._mqtt:
            self._mqtt.publish(
                channel=channel,
                message=message,
                qos=qos,
                retain=retain
            )

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
