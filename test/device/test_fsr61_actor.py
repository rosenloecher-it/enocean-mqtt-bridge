import json
import unittest
from collections import namedtuple
from datetime import datetime, timedelta, timezone

from paho.mqtt.client import MQTTMessage

from src.common.actor_command import ActorCommand
from src.common.switch_state import SwitchState
from src.device.fsr61_actor import Fsr61Actor
from src.device.fsr61_eep import Fsr61Action, Fsr61Eep, Fsr61Command
from src.device.rocker_switch_tools import RockerSwitchTools, RockerAction, RockerButton, RockerPress
from src.enocean_connector import EnoceanMessage
from test.setup_test import SetupTest


class _MockDevice(Fsr61Actor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self._enocean_id = 0xffffffff

        self.messages = []
        self.packets = []

    def _now(self):
        return self.now

    def _publish_mqtt(self, message: str, mqtt_channel: str = None):
        self.messages.append(message)

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)


class TestFsr61Actor(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

        self.device = _MockDevice()
        self.device.now = datetime(2020, 1, 1, 2, 2, 3, tzinfo=timezone.utc)

    def test_proceed_enocean(self):
        device = self.device

        Scenario = namedtuple("Scenario", ["rocker_button", "expected_state"])

        scenarios = [
            Scenario(RockerButton.ROCK3, "on"),
            Scenario(RockerButton.ROCK2, "off"),
        ]

        for scenario in scenarios:
            action = RockerAction(RockerPress.PRESS_SHORT, scenario.rocker_button)
            packet = RockerSwitchTools.create_packet(action)
            packet.dBm = -55
            message = EnoceanMessage(payload=packet, enocean_id=device._enocean_id)

            device.messages = []
            device.process_enocean_message(message)
            self.assertEqual(device._mqtt_last_refresh, device._now())

            self.assertEqual(len(device.messages), 1)
            result = json.loads(device.messages[0])

            compare = {'timestamp': '2020-01-01T02:02:03+00:00', 'state': scenario.expected_state, 'rssi': -55}
            self.assertEqual(result, compare)

    def test_mqtt_command(self):
        device = self.device

        def process_mqtt_message_to_action(command) -> Fsr61Action:
            message = MQTTMessage()
            message.payload = command

            device.packets.clear()
            device.process_mqtt_message(message)

            self.assertEqual(len(device.packets), 1)
            action = Fsr61Eep.extract_packet(device.packets[0])
            return action

        # loop 1 - init with 100
        action = process_mqtt_message_to_action(b"on")
        self.assertEqual(action.command, Fsr61Command.SWITCHING)
        self.assertEqual(action.switch_state, SwitchState.ON)

        action = process_mqtt_message_to_action(b"off")
        self.assertEqual(action.command, Fsr61Command.SWITCHING)
        self.assertEqual(action.switch_state, SwitchState.OFF)

        action = process_mqtt_message_to_action(b"update")
        self.assertEqual(action.command, Fsr61Command.STATUS_REQUEST)

    def test_cyclic_status_requests(self):
        d = self.device
        last_command = None  # type: ActorCommand

        def mock_execute_actor_command(command: ActorCommand):
            nonlocal last_command
            last_command = command

        def check_check_cyclic_tasks(now: datetime) -> ActorCommand:
            nonlocal last_command
            last_command = None
            d.now = now
            d.check_cyclic_tasks()
            return last_command

        d._execute_actor_command = mock_execute_actor_command

        time_now = d.now
        self.assertEqual(d._last_status_request, None)
        self.assertEqual(check_check_cyclic_tasks(time_now), ActorCommand.UPDATE)
        self.assertEqual(d._last_status_request, time_now)

        time_before = time_now
        time_now = time_before + timedelta(seconds=d.DEFAULT_REFRESH_RATE - 1)
        self.assertEqual(check_check_cyclic_tasks(time_now), None)
        self.assertEqual(d._last_status_request, time_before)

        time_now = time_now + timedelta(seconds=d.DEFAULT_REFRESH_RATE * 0.5)
        self.assertEqual(check_check_cyclic_tasks(time_now), ActorCommand.UPDATE)
        self.assertEqual(d._last_status_request, time_now)

# import unittest
#
# from src.device.rocker_actor import SwitchState
# from src.device.fsr61_actor import Fsr61Actor
# from src.tools.pickle_tools import PickleTools
# from test.setup_test import SetupTest
#
#
# class _MockDevice(Fsr61Actor):
#
#     def __init__(self):
#         self.now = None
#
#         super().__init__("mock")
#
#         self._enocean_id = 0xffffffff
#
#         self.messages = []
#         self.packets = []
#
#     def _now(self):
#         return self.now
#
#     def _publish_mqtt(self, message: str, mqtt_channel: str = None):
#         self.messages.append(message)
#
#     def _send_enocean_packet(self, packet, delay=0):
#         self.packets.append(packet)
#
#
# PACKET_OFF = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ktwSwVLGksSS/5LMGVY
# CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0swSwBldS4="""
#
#
# PACKET_ON = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ktQSwVLGksSS/5LMGVY
# CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0swSwBldS4="""
#
#
# class TestFsr61Actor(unittest.TestCase):
#
#     def setUp(self):
#         SetupTest.set_dummy_sender_id()
#
#     def test_extract_off(self):
#         packet = PickleTools.unpickle_packet(PACKET_OFF)
#
#         device = _MockDevice()
#         common = device._extract_packet_props(packet)
#         switch_state = device.extract_switch_state(common)
#
#         self.assertEqual(switch_state, SwitchState.ON)
#
#     def test_extract_on(self):
#         packet = PickleTools.unpickle_packet(PACKET_ON)
#
#         device = _MockDevice()
#         common = device._extract_packet_props(packet)
#         switch_state = device.extract_switch_state(common)
#
#         self.assertEqual(switch_state, SwitchState.OFF)
