import unittest
from collections import namedtuple
from typing import Dict, Union

from paho.mqtt.client import MQTTMessage

from src.device.base.rocker_actor import RockerSwitchAction, RockerActor
from src.device.rocker_switch.rocker_switch_tools import RockerSwitchTools, RockerAction, RockerPress, RockerButton
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools


class _MockDevice(RockerActor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self.messages = []
        self.packets = []

    def _now(self):
        return self.now

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)

    def _publish_mqtt(self, payload: Union[str, Dict], mqtt_channel: str = None):
        self.messages.append(payload)

    def process_enocean_message(self, message: EnoceanMessage):
        """dummy implementation of abstract method"""


class TestRockerActor(unittest.TestCase):

    def test_created_switch_packet(self):
        device = _MockDevice()
        packet = device._create_switch_packet(RockerSwitchAction.ON)

        extract = EnoceanTools.extract_props(packet=packet, eep=RockerSwitchTools.DEFAULT_EEP)

        self.assertEqual(extract, {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1})

    def test_process_mqtt_message(self):
        TestRun = namedtuple("TestRun", ["mqtt_command", "expected_action"])
        test_runs = [
            TestRun("learn", RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)),
            TestRun("on", RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)),
            TestRun("off", RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0)),
        ]

        for test_run in test_runs:
            device = _MockDevice()

            message = MQTTMessage()
            message.payload = "{0}".format(test_run.mqtt_command).encode()
            device.process_mqtt_message(message)

            # expected a "press" and "release" rocker packet, but checked is only the first packet
            created_action = RockerSwitchTools.extract_action_from_packet(device.packets[0]) if 2 == len(device.packets) else None

            self.assertEqual(test_run.expected_action, created_action)
