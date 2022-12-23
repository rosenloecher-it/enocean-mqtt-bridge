import copy
import unittest
from datetime import datetime, timezone, timedelta

from paho.mqtt.client import MQTTMessage

from src.common.device_exception import DeviceException
from src.device.eltako_fsb61.fsb61_actor import Fsb61Actor
from src.device.eltako_fsb61 import fsb61_actor
from src.device.eltako_fsb61.fsb61_eep import Fsb61CommandConverter, Fsb61Command, Fsb61CommandType, Fsb61State, Fsb61StateType, \
    Fsb61StateConverter
from src.device.eltako_fsb61.fsb61_shutter_position import Fsb61ShutterPosition
from src.enocean_connector import EnoceanMessage
from test.setup_test import SetupTest


TIME_DOWN_DRIVING = 18.0
TIME_DOWN_ROLLING = 4.0
TIME_UP_DRIVING = 22.0
TIME_UP_ROLLING = 6.0


TEST_CONFIG = {
    # enocean base
    "enocean_target": 0x03333333,
    "enocean_sender": 0x94444444,
    "device_type": "EltakoFsb61",

    # mqtt
    "mqtt_channel_state": "test/shutter/state",
    "mqtt_retain": False,
    "mqtt_channel_cmd": "test/shutter/cmd",

    # specific
    "storage_file": "./__work__/shutter.yaml",
    "time_up_rolling": 6,
    "time_up_driving": 10.1,
    "time_down_rolling": 4,
    "time_down_driving": 9,
}


class _MockFsb61Actor(Fsb61Actor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self._enocean_target = 0x03333333
        self._enocean_sender = 0x94444444

        self.messages = []
        self.packets = []

        # dummy config
        self._shutter_position.time_down_driving = TIME_DOWN_DRIVING
        self._shutter_position.time_down_rolling = TIME_DOWN_ROLLING
        self._shutter_position.time_up_driving = TIME_UP_DRIVING
        self._shutter_position.time_up_rolling = TIME_UP_ROLLING

        self._storage._data = {}
        self._storage.save = lambda: None

    def _now(self):
        return self.now

    @property
    def position(self):
        return self._shutter_position.value

    def _publish_mqtt(self, message: str, mqtt_channel: str = None):
        self.messages.append(message)

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)


class TestFsb61Actor(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

        self.device = _MockFsb61Actor()
        self.device.now = datetime(2020, 1, 1, 2, 2, 3, tzinfo=timezone.utc)

    def test_mqtt_to_single_command(self):
        device = self.device

        def process_mqtt_message_to_command(mqtt_command) -> Fsb61Command:
            message = MQTTMessage()
            message.payload = mqtt_command

            device.packets.clear()
            device.process_mqtt_message(message)

            self.assertEqual(len(device.packets), 1)
            fsb61_command = Fsb61CommandConverter.extract_packet(device.packets[0])
            return fsb61_command

        command = process_mqtt_message_to_command(b"learn")
        self.assertEqual(command.type, Fsb61CommandType.LEARN)

        command = process_mqtt_message_to_command(b"up")
        self.assertEqual(command.type, Fsb61CommandType.OPEN)
        expected_time = TIME_UP_DRIVING + TIME_UP_ROLLING + Fsb61Actor.POSITION_RESERVE_TIME
        self.assertEqual(command.time, expected_time)

        command = process_mqtt_message_to_command(b"down")
        self.assertEqual(command.type, Fsb61CommandType.CLOSE)
        expected_time = TIME_DOWN_DRIVING + TIME_DOWN_ROLLING + Fsb61Actor.POSITION_RESERVE_TIME
        self.assertEqual(command.time, expected_time)

    def test_seek_by_mqtt(self):
        device = self.device

        def process_mqtt_command(mqtt_command: str):
            message = MQTTMessage()
            message.payload = "{0}".format(mqtt_command).encode()
            device.process_mqtt_message(message)

        def simulate_status_via_send_command(command: Fsb61Command):
            device.now = device.now + timedelta(seconds=command.time)
            command_awnser = copy.deepcopy(command)
            command_awnser.sender = device._enocean_target
            packet = Fsb61CommandConverter.create_packet(command_awnser)
            message = EnoceanMessage(enocean_id=device._enocean_target, payload=packet)
            device.process_enocean_message(message)

        position1 = 70
        position2 = 50

        process_mqtt_command("{0}".format(position1))
        self.assertEqual(len(device.packets), 1)
        packet_command_1 = Fsb61CommandConverter.extract_packet(device.packets[0])
        self.assertEqual(packet_command_1.type, Fsb61CommandType.CLOSE)
        expected_time = TIME_DOWN_DRIVING + TIME_DOWN_ROLLING + Fsb61Actor.POSITION_RESERVE_TIME
        self.assertEqual(packet_command_1.time, expected_time)
        self.assertEqual(len(device._stored_device_commands), 2)  # a second command was stored

        simulate_status_via_send_command(device._stored_device_commands[0])
        packet_command_2 = Fsb61CommandConverter.extract_packet(device.packets[1])
        self.assertEqual(packet_command_2.type, Fsb61CommandType.OPEN)
        rolling = Fsb61ShutterPosition.ROLLING
        expected_time = round(TIME_UP_DRIVING * (rolling - position1) / rolling + TIME_UP_ROLLING, 1)
        self.assertEqual(packet_command_2.time, expected_time)
        self.assertEqual(device.position, 100)
        self.assertTrue(device._stored_device_commands is None)  # only 1 command
        self.assertTrue(device._stored_device_commands_time is None)  # only 1 command

        simulate_status_via_send_command(packet_command_2)
        self.assertEqual(round(device.position), 70)

        process_mqtt_command("{0}".format(position2))
        self.assertEqual(len(device.packets), 3)
        packet_command_3 = Fsb61CommandConverter.extract_packet(device.packets[2])
        self.assertTrue(device._stored_device_commands is None)  # only 1 command
        self.assertTrue(device._stored_device_commands_time is None)  # only 1 command
        self.assertEqual(packet_command_3.type, Fsb61CommandType.OPEN)
        expected_time = round(TIME_UP_DRIVING * (position1 - position2) / Fsb61ShutterPosition.ROLLING, 1)
        self.assertEqual(packet_command_3.time, expected_time)

    def test_seek_by_rocker_switches(self):
        """when moved via external rocker switches and only driving between end positions, tthese commands are sent."""
        device = self.device

        def simulate_status_packet(status_type):
            command = Fsb61State(type=status_type)
            packet = Fsb61StateConverter.create_packet(command)
            message = EnoceanMessage(enocean_id=device._enocean_target, payload=packet)
            device.process_enocean_message(message)

        simulate_status_packet(Fsb61StateType.CLOSING)
        simulate_status_packet(Fsb61StateType.STOPPED)
        self.assertEqual(device.position, 100)

        simulate_status_packet(Fsb61StateType.OPENING)
        simulate_status_packet(Fsb61StateType.STOPPED)
        self.assertEqual(device.position, 0)


class TestFsb61Validation(unittest.TestCase):

    def test_success(self):
        Fsb61Actor.validate_config(TEST_CONFIG, fsb61_actor.FSB61_JSONSCHEMA)

    def test_failure(self):
        with self.assertRaises(DeviceException):
            c = copy.deepcopy(TEST_CONFIG)
            c[fsb61_actor.CONFKEY_TIME_DOWN_DRIVING] = "invalid"
            Fsb61Actor.validate_config(c, fsb61_actor.FSB61_JSONSCHEMA)

        with self.assertRaises(DeviceException):
            c = copy.deepcopy(TEST_CONFIG)
            del c[fsb61_actor.CONFKEY_STORAGE_FILE]
            Fsb61Actor.validate_config(c, fsb61_actor.FSB61_JSONSCHEMA)
