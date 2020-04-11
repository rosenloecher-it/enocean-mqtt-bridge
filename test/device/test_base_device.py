import unittest
from datetime import datetime, timedelta

from enocean.protocol.constants import PACKET
from tzlocal import get_localzone

from src.device.conf_device_key import ConfDeviceKey
from src.device.base_device import BaseDevice
from src.tools import Tools
from test.mock_mqtt_publisher import MockMqttPublisher

PACKET_WIN_CLOSE = """
    gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
    a2V0X3R5cGVxA0sBWAQAAAByb3JncQRL9lgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
    Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
    aW1lCnEJQwoH5AMIEBMJB9fmcQqFcQtScQxYBAAAAGRhdGFxDV1xDihL9kvwSwVLh0uFS0pLIGVY
    CAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0tKSwBlWAYAAABzdGF0dXNxEUsgWAYAAABwYXJz
    ZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2NvdW50cRVL
    AFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMAAABkQm1x
    GUq2////WAYAAABzZW5kZXJxGl1xGyhLBUuHS4VLSmVYBQAAAGxlYXJucRyIdWIu
"""

PACKET_WIN_TILTED = """
    gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
    a2V0X3R5cGVxA0sBWAQAAAByb3JncQRL9lgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
    Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
    aW1lCnEJQwoH5AMIFBQSAtgpcQqFcQtScQxYBAAAAGRhdGFxDV1xDihL9kvQSwVLh0uFS0pLIGVY
    CAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0s6SwBlWAYAAABzdGF0dXNxEUsgWAYAAABwYXJz
    ZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2NvdW50cRVL
    AFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMAAABkQm1x
    GUrG////WAYAAABzZW5kZXJxGl1xGyhLBUuHS4VLSmVYBQAAAGxlYXJucRyIdWIu
"""

PACKET_WIN_OPEN = """
    gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
    a2V0X3R5cGVxA0sBWAQAAAByb3JncQRL9lgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
    Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
    aW1lCnEJQwoH5AMIFBQWDkikcQqFcQtScQxYBAAAAGRhdGFxDV1xDihL9kvgSwVLh0uFS0pLIGVY
    CAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0tASwBlWAYAAABzdGF0dXNxEUsgWAYAAABwYXJz
    ZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2NvdW50cRVL
    AFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMAAABkQm1x
    GUrA////WAYAAABzZW5kZXJxGl1xGyhLBUuHS4VLSmVYBQAAAGxlYXJucRyIdWIu
"""


class _TestExtractPropsDevice(BaseDevice):
    def process_enocean_message(self, message):
        raise NotImplementedError()  # not used


class TestBaseDeviceExtractProps(unittest.TestCase):

    def setUp(self):
        self.device = _TestExtractPropsDevice("test")
        self.device._enocean_func = 0x10
        self.device._enocean_id = 0x0587854a
        self.device._enocean_rorg = 0xf6
        self.device._enocean_type = 0x00

    def test_close(self):
        packet = Tools.unpickle(PACKET_WIN_CLOSE)

        comp = {'WIN': 3, 'T21': 1, 'NU': 0}
        data = self.device._extract_message(packet)
        self.assertEqual(data, comp)

    def test_tilted(self):
        packet = Tools.unpickle(PACKET_WIN_TILTED)

        comp = {'WIN': 1, 'T21': 1, 'NU': 0}
        data = self.device._extract_message(packet)
        self.assertEqual(data, comp)

    def test_open(self):
        packet = Tools.unpickle(PACKET_WIN_OPEN)

        comp = {'WIN': 2, 'T21': 1, 'NU': 0}
        data = self.device._extract_message(packet)
        self.assertEqual(data, comp)


class _TestTimeoutDevice(BaseDevice):

    def __init__(self, name):
        self.now = None
        super().__init__(name)

    def process_enocean_message(self, message):
        self._update_enocean_activity()

    def _now(self):
        return self.now


class TestBaseDeviceCheckAndSendOffline(unittest.TestCase):

    TIMEOUT = 1200  # 40 min

    def setUp(self):
        self.last_will = datetime.now().isoformat()

        self.mqtt_publisher = MockMqttPublisher()
        self.mqtt_publisher.open(None)

        self.device = _TestTimeoutDevice("test")

        self.device.set_config({
            ConfDeviceKey.ENOCEAN_ID.value: 0x0587854a,
            ConfDeviceKey.ENOCEAN_FUNC.value: 0x10,
            ConfDeviceKey.ENOCEAN_RORG.value: 0xf6,
            ConfDeviceKey.ENOCEAN_TYPE.value: 0x00,
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "dummy",
            ConfDeviceKey.MQTT_LAST_WILL.value: self.last_will,
            ConfDeviceKey.MQTT_TIME_OFFLINE.value: self.TIMEOUT,
        })

        self.device.set_mqtt_publisher(self.mqtt_publisher)

    def test_positive(self):
        now = datetime.now(tz=get_localzone())
        self.device.now = now

        self.device.process_enocean_message("")
        self.assertEqual(self.device._enocean_activity, now)

        now = now + timedelta(seconds=self.TIMEOUT - 2)
        self.device.now = now
        self.device.check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

        now = now + timedelta(seconds=self.TIMEOUT)
        self.device.now = now
        self.device.check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 1)
        self.assertEqual(self.mqtt_publisher.messages[0], self.last_will)

    def test_negative_without_last_will(self):
        self.device._mqtt_last_will = None

        self.device.now = datetime.now(tz=get_localzone())
        self.device.process_enocean_message("")

        self.device.now += timedelta(seconds=self.TIMEOUT + 2)
        self.device.check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

    def test_negative_without_timeout(self):
        self.device._mqtt_time_offline = None

        self.device.now = datetime.now(tz=get_localzone())
        self.device.process_enocean_message("")

        self.device.now += timedelta(seconds=self.TIMEOUT + 2)
        self.device.check_and_send_offline()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

    def test_packet_type_text(self):
        self.assertEqual(BaseDevice.packet_type_text(PACKET.RADIO), "RADIO")
        self.assertEqual(BaseDevice.packet_type_text(int(PACKET.RADIO)), "RADIO")
        self.assertEqual(BaseDevice.packet_type_text(None), "None")
