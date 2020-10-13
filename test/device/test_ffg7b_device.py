import datetime
import json
import unittest

from tzlocal import get_localzone

from src.device.conf_device_key import ConfDeviceKey
from src.device.ffg7b_sensor import HandleValue, FFG7BSensor, StorageKey
from src.enocean_connector import EnoceanMessage
from src.tools.pickle_tools import PickleTools
from test.device.test_base_device import PACKET_WIN_TILTED
from test.mock_mqtt_publisher import MockMqttPublisher


class _MockDevice(FFG7BSensor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self.sent_message = None

    def _now(self):
        return self.now

    def _publish_mqtt(self, message: str, mqtt_channel: str = None):
        self.sent_message = message


class TestEltakoFFG7BDevice(unittest.TestCase):

    def test_close(self):
        pass

    def test_implemented_abstract_methods(self):
        FFG7BSensor("test")

    def test_determine_and_store_since(self):

        device = _MockDevice()
        device.set_config({
            ConfDeviceKey.ENOCEAN_TARGET.value: 123,
            ConfDeviceKey.ENOCEAN_FUNC.value: 123,
            ConfDeviceKey.ENOCEAN_RORG.value: 123,
            ConfDeviceKey.ENOCEAN_TYPE.value: 123,
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "channel",

            ConfDeviceKey.WRITE_SINCE.value: True
        })

        time_1 = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_1
        time_since = device._determine_and_store_since(HandleValue.TILTED)
        self.assertEqual(time_since, time_1)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_1)
        self.assertEqual(value_stored, HandleValue.TILTED.value)

        time_2 = datetime.datetime(2020, 1, 2, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_2
        time_since = device._determine_and_store_since(HandleValue.TILTED)
        self.assertEqual(time_since, time_1)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_1)
        self.assertEqual(value_stored, HandleValue.TILTED.value)

        time_3 = datetime.datetime(2020, 1, 3, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_3
        time_since = device._determine_and_store_since(HandleValue.OPEN)
        self.assertEqual(time_since, time_3)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, HandleValue.OPEN.value)

        time_4 = datetime.datetime(2020, 1, 3, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_4
        time_since = device._determine_and_store_since(HandleValue.OFFLINE)
        self.assertEqual(time_since, time_4)
        time_stored = device._storage.get(StorageKey.TIME_ERROR.value)
        value_stored = device._storage.get(StorageKey.VALUE_ERROR.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, HandleValue.OFFLINE.value)

        time_5 = datetime.datetime(2020, 1, 4, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_5
        time_since = device._determine_and_store_since(HandleValue.OFFLINE)
        self.assertEqual(time_since, time_4)
        time_stored = device._storage.get(StorageKey.TIME_ERROR.value)
        value_stored = device._storage.get(StorageKey.VALUE_ERROR.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, HandleValue.OFFLINE.value)

        time_6 = datetime.datetime(2020, 1, 5, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_6
        time_since = device._determine_and_store_since(HandleValue.OPEN)
        self.assertEqual(time_since, time_3)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, HandleValue.OPEN.value)

        time_7 = datetime.datetime(2020, 1, 6, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_7
        time_since = device._determine_and_store_since(HandleValue.OFFLINE)
        self.assertEqual(time_since, time_7)
        time_stored = device._storage.get(StorageKey.TIME_ERROR.value)
        value_stored = device._storage.get(StorageKey.VALUE_ERROR.value)
        self.assertEqual(time_stored, time_7)
        self.assertEqual(value_stored, HandleValue.OFFLINE.value)

    def test_proceed_enocean(self):
        enocean_id = 0x05555555

        device = _MockDevice()
        device.set_config({
            ConfDeviceKey.ENOCEAN_TARGET.value: enocean_id,
            ConfDeviceKey.ENOCEAN_RORG.value: 0xf6,
            ConfDeviceKey.ENOCEAN_FUNC.value: 0x10,
            ConfDeviceKey.ENOCEAN_TYPE.value: 0x00,
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "channel",

            ConfDeviceKey.WRITE_SINCE.value: True
        })

        time_1 = datetime.datetime.now(tz=get_localzone())

        message = EnoceanMessage(
            payload=PickleTools.unpickle(PACKET_WIN_TILTED),
            enocean_id=enocean_id
        )
        device.now = time_1
        device.process_enocean_message(message)

        sent_data = json.loads(device.sent_message)
        self.assertEqual(sent_data, {
            'TIMESTAMP': time_1.isoformat(),
            'SINCE': time_1.isoformat(),
            'RSSI': -58,
            'STATE': 'TILTED'
        })


# TODO move to ffg7b
class _TestTimeoutDevice(FFG7BSensor):

    def __init__(self, name):
        self.now = None
        super().__init__(name)

        self._mqtt_last_will = '{"STATE": "OFFLINE", "INFO": "last will"}'

    def process_enocean_message(self, message):
        self._enocean_activity = self._now()

    def _now(self):
        return self.now


class TestBaseDeviceCheckAndSendOffline(unittest.TestCase):

    TIMEOUT = 1200  # 40 min

    def setUp(self):
        self.last_will = datetime.datetime.now().isoformat()

        self.mqtt_publisher = MockMqttPublisher()
        self.mqtt_publisher.open(None)

        self.device = _TestTimeoutDevice("test")

        self.device.set_config({
            ConfDeviceKey.ENOCEAN_TARGET.value: 0x0587854a,
            ConfDeviceKey.ENOCEAN_FUNC.value: 0x10,
            ConfDeviceKey.ENOCEAN_RORG.value: 0xf6,
            ConfDeviceKey.ENOCEAN_TYPE.value: 0x00,
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "dummy",
            ConfDeviceKey.MQTT_LAST_WILL.value: self.last_will,
            ConfDeviceKey.TIME_OFFLINE_MSG.value: self.TIMEOUT,
        })

        self.device.set_mqtt_publisher(self.mqtt_publisher)

    def test_positive(self):
        now = datetime.datetime.now(tz=get_localzone())
        self.device.now = now

        self.device.process_enocean_message("")
        self.assertEqual(self.device._enocean_activity, now)

        now = now + datetime.timedelta(seconds=self.TIMEOUT - 2)
        self.device.now = now
        self.device.check_cyclic_tasks()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

        now = now + datetime.timedelta(seconds=self.TIMEOUT)
        self.device.now = now
        self.device.check_cyclic_tasks()
        self.assertEqual(len(self.mqtt_publisher.messages), 1)
        self.assertEqual(self.mqtt_publisher.messages[0], self.last_will)

    def test_negative_without_last_will(self):
        self.device._mqtt_last_will = None

        self.device.now = datetime.datetime.now(tz=get_localzone())
        self.device.process_enocean_message("")

        self.device.now += datetime.timedelta(seconds=self.TIMEOUT + 2)
        self.device.check_cyclic_tasks()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)

    def test_negative_without_timeout(self):
        self.device._time_offline_msg = None

        self.device.now = datetime.datetime.now(tz=get_localzone())
        self.device.process_enocean_message("")

        self.device.now += datetime.timedelta(seconds=self.TIMEOUT + 2)
        self.device.check_cyclic_tasks()
        self.assertEqual(len(self.mqtt_publisher.messages), 0)
