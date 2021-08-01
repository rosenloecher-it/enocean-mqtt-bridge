import datetime
import json
import unittest

from paho.mqtt.client import MQTTMessage

from src.common.actor_command import ActorCommand
from src.common.switch_state import SwitchState
from src.device.eltako.fud61_actor import Fud61Actor
from src.device.eltako.fud61_eep import Fud61Action, Fud61Eep, Fud61Command
from src.enocean_connector import EnoceanMessage
from src.tools.pickle_tools import PickleTools
from test.setup_test import SetupTest

PACKET_STATUS_ON_33 = """
gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
a2V0X3R5cGVxA0sBWAQAAAByb3JncQRLpVgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
aW1lCnEJQwoH5AMdECwNB6j9cQqFcQtScQxYBAAAAGRhdGFxDV1xDihLpUsCSyFLAEsJSwVLGksu
S3xLAGVYCAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0s3SwBlWAYAAABzdGF0dXNxEUsAWAYA
AABwYXJzZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2Nv
dW50cRVLAFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMA
AABkQm1xGUrJ////WAYAAABzZW5kZXJxGl1xGyhLBUsaSy5LfGVYBQAAAGxlYXJucRyJdWIu
"""
# {'RSSI': -55, 'COM': 2, 'COM_EXT': 'Command ID 2', 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'EDIMR_EXT': 'Absolute value',
# 'STR': 0, 'STR_EXT': 'No', 'SW': 1, 'SW_EXT': 'On'}


class _MockDevice(Fud61Actor):

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


class TestFud61Actor(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

        self.device = _MockDevice()
        self.device.now = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=datetime.timezone.utc)

    def test_proceed_enocean(self):
        device = self.device

        packet = PickleTools.unpickle(PACKET_STATUS_ON_33)
        message = EnoceanMessage(payload=packet, enocean_id=device._enocean_id)

        device.process_enocean_message(message)

        self.assertEqual(len(device.messages), 1)
        result = json.loads(device.messages[0])

        compare = {'timestamp': '2020-01-01T02:02:03+00:00', 'state': 'on', 'rssi': -55, 'dim_state': 33}
        self.assertEqual(result, compare)

    def test_proceed_enocean_2(self):
        device = self.device

        action = Fud61Action(Fud61Command.DIMMING, dim_state=90)
        packet = Fud61Eep.create_packet(action)
        packet.dBm = -55
        message = EnoceanMessage(payload=packet, enocean_id=device._enocean_id)
        device.process_enocean_message(message)

        self.assertEqual(device._last_dim_state, action.dim_state)
        self.assertEqual(device._last_status_request, device._now())

        self.assertEqual(len(device.messages), 1)
        result = json.loads(device.messages[0])

        compare = {'timestamp': '2020-01-01T02:02:03+00:00', 'state': 'on', 'rssi': -55, 'dim_state': 90}
        self.assertEqual(result, compare)

    def test_mqtt_command(self):
        device = self.device

        def process_mqtt_message_to_action(command) -> Fud61Action:
            message = MQTTMessage()
            message.payload = command

            device.packets.clear()
            device.process_mqtt_message(message)

            self.assertEqual(len(device.packets), 1)
            action = Fud61Eep.extract_packet(device.packets[0])
            return action

        # loop 1 - init with 100
        action = process_mqtt_message_to_action(b"100")
        self.assertEqual(action.command, Fud61Command.DIMMING)
        self.assertEqual(action.switch_state, SwitchState.ON)
        self.assertEqual(action.dim_state, 100)

        # loop 2 - set dim value
        action = process_mqtt_message_to_action(b"50")
        self.assertEqual(action.command, Fud61Command.DIMMING)
        self.assertEqual(action.switch_state, SwitchState.ON)
        self.assertEqual(action.dim_state, 50)

        # simulate state
        action_state_simu = Fud61Action(Fud61Command.DIMMING, dim_state=action.dim_state)
        packet_state_simu = Fud61Eep.create_packet(action_state_simu)
        message_state_simu = EnoceanMessage(payload=packet_state_simu, enocean_id=device._enocean_id)
        device.process_enocean_message(message_state_simu)
        self.assertEqual(device._last_dim_state, action.dim_state)

        # loop 4 - off
        action = process_mqtt_message_to_action(b"off")
        self.assertEqual(action.command, Fud61Command.DIMMING)
        self.assertEqual(action.switch_state, SwitchState.OFF)
        self.assertEqual(action.dim_state, 0)

        # loop 5 - on with old dim state
        action = process_mqtt_message_to_action(b"on")
        self.assertEqual(action.command, Fud61Command.DIMMING)
        self.assertEqual(action.switch_state, SwitchState.ON)
        self.assertEqual(action.dim_state, 50)

        # loop 6 - request update
        action = process_mqtt_message_to_action(b"update")
        self.assertEqual(action.command, Fud61Command.STATUS_REQUEST)

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
        time_now = time_before + datetime.timedelta(seconds=d.DEFAULT_REFRESH_RATE - 1)
        self.assertEqual(check_check_cyclic_tasks(time_now), None)
        self.assertEqual(d._last_status_request, time_before)

        time_now = time_now + datetime.timedelta(seconds=d.DEFAULT_REFRESH_RATE * 0.5)
        self.assertEqual(check_check_cyclic_tasks(time_now), ActorCommand.UPDATE)
        self.assertEqual(d._last_status_request, time_now)
