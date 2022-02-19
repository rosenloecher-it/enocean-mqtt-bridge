import datetime
import logging
import unittest

from paho.mqtt.client import MQTTMessage
from tzlocal import get_localzone

from src.device.base import device
from src.device.base.device import Device
from test.mock_mqtt_publisher import MockMqttPublisher

_logger = logging.getLogger(__name__)
_dummy_logger = _logger


class _TestTimeoutDevice(Device):

    def __init__(self):
        self.now = datetime.datetime.now(tz=get_localzone()) - datetime.timedelta(minutes=10)
        super().__init__("_TestTimeoutDevice")

        self._mqtt_last_will = '{"status": "offline", "info": "last will"}'
        self._last_refresh = self._now()

    def process_enocean_message(self, message):
        self._last_refresh = self._now()

    def process_mqtt_message(self, message: MQTTMessage):
        pass

    def _now(self):
        return self.now

    def name(self):
        return self.__class__.__name__

    @property
    def _logger(self):
        return _dummy_logger


class TestBaseDeviceCheckAndSendOffline(unittest.TestCase):

    TIMEOUT = 1200  # 40 min

    def setUp(self):
        self.last_will = datetime.datetime.now().isoformat()

        self.mqtt_publisher = MockMqttPublisher()
        # self.mqtt_publisher.open(None)

        self.device = _TestTimeoutDevice()

        self.device._set_config({
            device.CONFKEY_MQTT_CHANNEL_CMD: "dummy-cmd",
            device.CONFKEY_MQTT_CHANNEL_STATE: "dummy",
            device.CONFKEY_MQTT_LAST_WILL: self.last_will,
            device.CONFKEY_MQTT_TIME_OFFLINE: self.TIMEOUT,
        }, ["*"])

        self.device.set_mqtt_publisher(self.mqtt_publisher)

    def test_positive(self):
        now = datetime.datetime.now(tz=get_localzone())
        self.device.now = now
        self.device._last_refresh_time = now

        self.device.process_enocean_message("")
        self.assertEqual(self.device._last_refresh, now)

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
