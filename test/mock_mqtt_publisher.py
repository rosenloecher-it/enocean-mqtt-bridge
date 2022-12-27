from src.mqtt_publisher import MqttPublisher


class MockMqttPublisher(MqttPublisher):

    def __init__(self):
        super().__init__()

        self.messages = []
        self.will = None

    def publish(self, channel, payload, qos=0, retain=False):
        assert isinstance(payload, str)
        self.messages.append(payload)

    def store_last_will(self, channel, message, qos=0, retain=False):
        assert isinstance(message, str)
        self.will = message
