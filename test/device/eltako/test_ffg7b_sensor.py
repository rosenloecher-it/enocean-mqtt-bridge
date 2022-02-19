import datetime
import json
import unittest

from tzlocal import get_localzone

from src.device.base.device import CONFKEY_MQTT_CHANNEL_STATE, CONFKEY_ENOCEAN_SENDER, CONFKEY_ENOCEAN_TARGET
from src.device.eltako.ffg7b_sensor import HandleValue, FFG7BSensor, StorageKey
from src.enocean_connector import EnoceanMessage
from src.tools.pickle_tools import PickleTools
from test.device.base.test_base_device import PACKET_WIN_TILTED


class _MockDevice(FFG7BSensor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self.sent_message = None
        self._storage.empty()

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
            CONFKEY_ENOCEAN_SENDER: 123,
            CONFKEY_ENOCEAN_TARGET: 123,
            CONFKEY_MQTT_CHANNEL_STATE: "channel",
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
        config = {
            CONFKEY_ENOCEAN_TARGET: enocean_id,
            CONFKEY_MQTT_CHANNEL_STATE: "channel",
            CONFKEY_ENOCEAN_SENDER: 1234,
        }
        device.set_config(config)

        time_1 = datetime.datetime.now(tz=get_localzone())

        message = EnoceanMessage(
            payload=PickleTools.unpickle(PACKET_WIN_TILTED),
            enocean_id=enocean_id
        )
        device.now = time_1
        device.process_enocean_message(message)

        sent_data = json.loads(device.sent_message)
        self.assertEqual(sent_data, {
            'device': 'mock',
            'timestamp': time_1.isoformat(),
            'since': time_1.isoformat(),
            'status': 'tilted'
        })
