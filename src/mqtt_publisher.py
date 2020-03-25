

class MqttPublisher:

    def __init__(self):
        self._mqtt = None
        self._open = False

    def set_mqtt(self, mqtt):
        self._mqtt = mqtt

    def open(self):
        self._open = True

    def close(self):
        self._mqtt = None
        self._open = False

    def publish(self, channel: str, message: str, qos: int = 0, retain: bool = False):
        if self._open:
            self._mqtt.publish(
                topic=channel,
                payload=message,
                qos=qos,
                retain=retain
            )

    def will_set(self, channel: str, message: str, qos: int = 0, retain: bool = False):
        self._mqtt.will_set(
            topic=channel,
            payload=message,
            qos=qos,
            retain=retain
        )
