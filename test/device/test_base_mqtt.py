import datetime
import logging
import unittest

from paho.mqtt.client import MQTTMessage
from tzlocal import get_localzone

from src.common.conf_device_key import ConfDeviceKey
from src.device.base_mqtt import BaseMqtt
from test.mock_mqtt_publisher import MockMqttPublisher

_logger = logging.getLogger(__name__)
_dummy_logger = _logger


class _TestTimeoutDevice(BaseMqtt):

    def __init__(self):
        self.now = None
        super().__init__()

        self._mqtt_last_will = '{"STATE": "OFFLINE", "INFO": "last will"}'

    def process_enocean_message(self, message):
        self._mqtt_last_refresh = self._now()

    def process_mqtt_message(self, message: MQTTMessage):
        pass

    def _now(self):
        return self.now

    @property
    def _logger(self):
        return _dummy_logger


class TestBaseDeviceCheckAndSendOffline(unittest.TestCase):

    TIMEOUT = 1200  # 40 min

    def setUp(self):
        self.last_will = datetime.datetime.now().isoformat()

        self.mqtt_publisher = MockMqttPublisher()
        self.mqtt_publisher.open(None)

        self.device = _TestTimeoutDevice()

        self.device.set_config({
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "dummy",
            ConfDeviceKey.MQTT_LAST_WILL.value: self.last_will,
            ConfDeviceKey.MQTT_TIME_OFFLINE.value: self.TIMEOUT,
        })

        self.device.set_mqtt_publisher(self.mqtt_publisher)

    def test_positive(self):
        now = datetime.datetime.now(tz=get_localzone())
        self.device.now = now

        self.device.process_enocean_message("")
        self.assertEqual(self.device._mqtt_last_refresh, now)

        now = now + datetime.timedelta(seconds=self.TIMEOUT - 2)
        self.device.now = now
        self.device._check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

        now = now + datetime.timedelta(seconds=self.TIMEOUT)
        self.device.now = now
        self.device._check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 1)
        self.assertEqual(self.mqtt_publisher.messages[0], self.last_will)

    def test_negative_without_last_will(self):
        self.device._mqtt_last_will = None

        self.device.now = datetime.datetime.now(tz=get_localzone())
        self.device.process_enocean_message("")

        self.device.now += datetime.timedelta(seconds=self.TIMEOUT + 2)
        self.device._check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

    def test_negative_without_timeout(self):
        self.device._mqtt_time_offline = None

        self.device.now = datetime.datetime.now(tz=get_localzone())
        self.device.process_enocean_message("")

        self.device.now += datetime.timedelta(seconds=self.TIMEOUT + 2)
        self.device._check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)
