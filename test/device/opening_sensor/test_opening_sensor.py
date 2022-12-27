import datetime
import os
import unittest
from collections import namedtuple
from typing import Dict, Union

from tzlocal import get_localzone

from src.device.base.device import CONFKEY_ENOCEAN_SENDER
from src.device.base.device import CONFKEY_MQTT_CHANNEL_STATE, CONFKEY_ENOCEAN_TARGET
from src.device.opening_sensor.opening_sensor import OpeningSensor, StorageKey, StateValue
from src.enocean_connector import EnoceanMessage
from src.storage import CONFKEY_STORAGE_FILE, CONFKEY_STORAGE_MAX_AGE_SECS
from src.tools.pickle_tools import PickleTools
from test.device.opening_sensor import sample_telegrams
from test.setup_test import SetupTest

TestItem = namedtuple("TestItem", ["packet", "expected_status", "expected_rssi"])


class MockedOpeningSensor(OpeningSensor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self.sent_message = None

    def _now(self):
        return self.now

    def _publish_mqtt(self, payload: Union[str, Dict], mqtt_channel: str = None):
        self.sent_message = payload


class TestOpeningSensor(unittest.TestCase):

    def test_close(self):
        pass

    def test_implemented_abstract_methods(self):
        OpeningSensor("test")

    def test_determine_and_store_since(self):

        device = MockedOpeningSensor()
        device.set_config({
            CONFKEY_ENOCEAN_SENDER: 123,
            CONFKEY_ENOCEAN_TARGET: 123,
            CONFKEY_MQTT_CHANNEL_STATE: "channel",
        })

        time_1 = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_1
        time_since = device._determine_and_store_since(StateValue.TILTED)
        self.assertEqual(time_since, time_1)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_1)
        self.assertEqual(value_stored, StateValue.TILTED.value)

        time_2 = datetime.datetime(2020, 1, 2, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_2
        time_since = device._determine_and_store_since(StateValue.TILTED)
        self.assertEqual(time_since, time_1)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_1)
        self.assertEqual(value_stored, StateValue.TILTED.value)

        time_3 = datetime.datetime(2020, 1, 3, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_3
        time_since = device._determine_and_store_since(StateValue.OPEN)
        self.assertEqual(time_since, time_3)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, StateValue.OPEN.value)

        time_4 = datetime.datetime(2020, 1, 3, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_4
        time_since = device._determine_and_store_since(StateValue.OFFLINE)
        self.assertEqual(time_since, time_4)
        time_stored = device._storage.get(StorageKey.TIME_ERROR.value)
        value_stored = device._storage.get(StorageKey.VALUE_ERROR.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, StateValue.OFFLINE.value)

        time_5 = datetime.datetime(2020, 1, 4, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_5
        time_since = device._determine_and_store_since(StateValue.OFFLINE)
        self.assertEqual(time_since, time_4)
        time_stored = device._storage.get(StorageKey.TIME_ERROR.value)
        value_stored = device._storage.get(StorageKey.VALUE_ERROR.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, StateValue.OFFLINE.value)

        time_6 = datetime.datetime(2020, 1, 5, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_6
        time_since = device._determine_and_store_since(StateValue.OPEN)
        self.assertEqual(time_since, time_3)
        time_stored = device._storage.get(StorageKey.TIME_SUCCESS.value)
        value_stored = device._storage.get(StorageKey.VALUE_SUCCESS.value)
        self.assertEqual(time_stored, time_3)
        self.assertEqual(value_stored, StateValue.OPEN.value)

        time_7 = datetime.datetime(2020, 1, 6, 2, 2, 3, tzinfo=get_localzone())
        device.now = time_7
        time_since = device._determine_and_store_since(StateValue.OFFLINE)
        self.assertEqual(time_since, time_7)
        time_stored = device._storage.get(StorageKey.TIME_ERROR.value)
        value_stored = device._storage.get(StorageKey.VALUE_ERROR.value)
        self.assertEqual(time_stored, time_7)
        self.assertEqual(value_stored, StateValue.OFFLINE.value)


class TestOpeningSensorRestoreState(unittest.TestCase):

    def setUp(self):
        work_dir = SetupTest.ensure_clean_work_dir()

        self.storage_path = os.path.join(work_dir, "device_storage.yaml")
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
            self.assertFalse(os.path.exists(self.storage_path))

        self.device = MockedOpeningSensor()

        self.device.now = datetime.datetime(2022, 12, 27, 10, 0, 0, tzinfo=get_localzone())

        self.time_last_observation = 120  # different to default value

        self.device.set_config({
            CONFKEY_ENOCEAN_SENDER: 123,
            CONFKEY_ENOCEAN_TARGET: 123,
            CONFKEY_MQTT_CHANNEL_STATE: "channel",
            CONFKEY_STORAGE_FILE: self.storage_path,
            CONFKEY_STORAGE_MAX_AGE_SECS: self.time_last_observation,
        })

    def test_success_status(self):
        d = self.device
        time1 = d.now

        d._restore_last_state()
        self.assertEqual(None, d.sent_message)

        d._determine_and_store_since(StateValue.OPEN)
        self.assertTrue(os.path.exists(self.storage_path))

        d.now = d.now + datetime.timedelta(seconds=self.time_last_observation - 2)
        d._restore_last_state()

        self.assertEqual({
            "device": "mock",
            "timestamp": time1,
            "since": time1,
            "status": "open",
        }, d.sent_message)

        d.sent_message = None  # reset

        d.now = d.now + datetime.timedelta(seconds=self.time_last_observation + 2)
        d._restore_last_state()
        self.assertEqual(None, d.sent_message)

    def test_error_status(self):
        d = self.device

        d._restore_last_state()
        self.assertEqual(None, d.sent_message)

        d._determine_and_store_since(StateValue.OPEN)
        self.assertTrue(os.path.exists(self.storage_path))

        d.now = d.now + datetime.timedelta(seconds=self.time_last_observation - 2)
        d._determine_and_store_since(StateValue.OFFLINE)

        d.now = d.now + datetime.timedelta(seconds=self.time_last_observation - 2)
        d._restore_last_state()

        self.assertEqual(None, d.sent_message)


class TestEltakoFFG7B(unittest.TestCase):

    def test_proceed_enocean(self):
        enocean_id = 0x05555555

        device = MockedOpeningSensor()
        config = {
            CONFKEY_ENOCEAN_TARGET: enocean_id,
            CONFKEY_MQTT_CHANNEL_STATE: "channel",
            CONFKEY_ENOCEAN_SENDER: 1234,
        }
        device.set_config(config)

        time_1 = datetime.datetime.now(tz=get_localzone())

        message = EnoceanMessage(
            payload=PickleTools.unpickle(sample_telegrams.PACKET_ELTAKO_FFG7B_TILTED),
            enocean_id=enocean_id
        )
        device.now = time_1
        device.process_enocean_message(message)

        self.assertEqual({
            "device": "mock",
            "timestamp": time_1,
            "since": time_1,
            "status": "tilted",
            "rssi": -58,
        }, device.sent_message)


class TestNodonSdo2105(unittest.TestCase):

    def test_proceed_enocean(self):
        test_times = [
            TestItem(packet=sample_telegrams.PACKET_NODON_SDO_2105_OPEN, expected_status="open", expected_rssi=-45),
            TestItem(packet=sample_telegrams.PACKET_NODON_SDO_2105_CLOSED, expected_status="closed", expected_rssi=-45),
            TestItem(packet=sample_telegrams.PACKET_NODON_SDO_2105_UPDATE_OPEN, expected_status="open", expected_rssi=-49),
            TestItem(packet=sample_telegrams.PACKET_NODON_SDO_2105_UPDATE_CLOSED, expected_status="closed", expected_rssi=-48),
        ]

        for test_item in test_times:
            packet = PickleTools.unpickle_packet(test_item.packet)
            enocean_id = packet.sender_int

            device = MockedOpeningSensor()
            config = {
                CONFKEY_ENOCEAN_TARGET: enocean_id,
                CONFKEY_MQTT_CHANNEL_STATE: "channel",
            }
            device.set_config(config)

            time_1 = datetime.datetime.now(tz=get_localzone())

            message = EnoceanMessage(
                payload=packet,
                enocean_id=packet.sender
            )
            device.now = time_1
            device.process_enocean_message(message)

            self.assertEqual({
                "device": "mock",
                "timestamp": time_1,
                "since": time_1,
                "status": test_item.expected_status,
                "rssi": test_item.expected_rssi,
            }, device.sent_message)


class TestEltakoFtkb(unittest.TestCase):

    def test_proceed_enocean(self):
        test_times = [
            TestItem(packet=sample_telegrams.PACKET_ELTAKO_FTKB_OPEN_1, expected_status="open", expected_rssi=-58),
            TestItem(packet=sample_telegrams.PACKET_ELTAKO_FTKB_OPEN_2, expected_status="open", expected_rssi=-76),
            TestItem(packet=sample_telegrams.PACKET_ELTAKO_FTKB_CLOSED_1, expected_status="closed", expected_rssi=-64),
            TestItem(packet=sample_telegrams.PACKET_ELTAKO_FTKB_CLOSED_2, expected_status="closed", expected_rssi=-65),
        ]

        for test_item in test_times:
            packet = PickleTools.unpickle_packet(test_item.packet)
            enocean_id = packet.sender_int

            device = MockedOpeningSensor()
            config = {
                CONFKEY_ENOCEAN_TARGET: enocean_id,
                CONFKEY_MQTT_CHANNEL_STATE: "channel",
            }
            device.set_config(config)

            time_1 = datetime.datetime.now(tz=get_localzone())

            message = EnoceanMessage(
                payload=packet,
                enocean_id=packet.sender
            )
            device.now = time_1
            device.process_enocean_message(message)

            self.assertEqual({
                "device": "mock",
                "timestamp": time_1,
                "since": time_1,
                "status": test_item.expected_status,
                "rssi": test_item.expected_rssi,
            }, device.sent_message)
