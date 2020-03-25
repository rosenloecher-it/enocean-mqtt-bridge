from src.mqtt_publisher import MqttPublisher


class MockMqttPublisher(MqttPublisher):

    def __init__(self):
        super().__init__()

        self.messages = []
        self.will = None

    def publish(self, channel, message, qos=0, retain=False):
        if self._open:
            assert isinstance(message, str)
            self.messages.append(message)

    def will_set(self, channel, message, qos=0, retain=False):
        assert isinstance(message, str)
        self.will = message
