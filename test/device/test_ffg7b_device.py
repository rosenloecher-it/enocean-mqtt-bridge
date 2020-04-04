import datetime
import json
import unittest

from tzlocal import get_localzone

from src.device.conf_device_key import ConfDeviceKey
from src.device.ffg7b_device import HandleValue, FFG7BDevice, ConfDeviceExKey, StorageKey
from src.enocean_connector import EnoceanMessage
from src.tools import Tools
from test.device.test_base_device import PACKET_WIN_TILTED


class _MockDevice(FFG7BDevice):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self.sent_message = None

    def _now(self):
        return self.now

    def _publish(self, message):
        self.sent_message = message


class TestEltakoFFG7BDevice(unittest.TestCase):

    def test_close(self):
        pass

    def test_determine_and_store_since(self):

        device = _MockDevice()
        device.set_config({
            ConfDeviceKey.ENOCEAN_ID.value: 123,
            ConfDeviceKey.ENOCEAN_FUNC.value: 123,
            ConfDeviceKey.ENOCEAN_RORG.value: 123,
            ConfDeviceKey.ENOCEAN_TYPE.value: 123,
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "channel",

            ConfDeviceExKey.WRITE_SINCE.value: True
        })

        time_1 = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_1
        time_since = device._determine_and_store_since(HandleValue.TILTED)
        self.assertEqual(time_since, time_1)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCESS.value)
        self.assertEqual(time_stored, time_1)
        self.assertEqual(value_stored, HandleValue.TILTED.value)

        time_2 = datetime.datetime(2020, 1, 2, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_2
        time_since = device._determine_and_store_since(HandleValue.TILTED)
        self.assertEqual(time_since, time_1)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCESS.value)
        self.assertEqual(time_stored, time_1)
        self.assertEqual(value_stored, HandleValue.TILTED.value)

        time_3 = datetime.datetime(2020, 1, 3, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_3
        time_since = device._determine_and_store_since(HandleValue.OPEN)
        self.assertEqual(time_since, time_3)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCESS.value)
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
        value_stored = device._storage.get(StorageKey.VALUE_SUCESS.value)
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
            ConfDeviceKey.ENOCEAN_ID.value: enocean_id,
            ConfDeviceKey.ENOCEAN_RORG.value: 0xf6,
            ConfDeviceKey.ENOCEAN_FUNC.value: 0x10,
            ConfDeviceKey.ENOCEAN_TYPE.value: 0x00,
            ConfDeviceKey.MQTT_CHANNEL_STATE.value: "channel",

            ConfDeviceExKey.WRITE_SINCE.value: True
        })

        time_1 = datetime.datetime.now(tz=get_localzone())

        message = EnoceanMessage(
            payload=Tools.unpickle(PACKET_WIN_TILTED),
            enocean_id=enocean_id
        )
        device.now = time_1
        device.proceed_enocean(message)

        sent_data = json.loads(device.sent_message)
        self.assertEqual(sent_data, {
            'TIMESTAMP': time_1.isoformat(),
            'SINCE': time_1.isoformat(),
            'RSSI': -58,
            'VALUE': 'TILTED'
        })
