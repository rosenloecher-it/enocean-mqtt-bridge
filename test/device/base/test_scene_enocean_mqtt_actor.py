import logging
import unittest
from typing import List
from paho.mqtt.client import MQTTMessage

from enocean.protocol.packet import RadioPacket
from src.device.base import device
from src.device.base.scene_actor import SceneActor, CONFKEY_ROCKER_SCENES
from src.device.eltako_fsb61.fsb61_eep import Fsb61Command, Fsb61CommandType, Fsb61CommandConverter
from src.device.rocker_switch.rocker_switch_tools import RockerSwitchTools, RockerAction, RockerPress, RockerButton
from src.enocean_connector import EnoceanMessage

_logger = logging.getLogger(__name__)
_dummy_logger = _logger


class _TestRockerSceneActor(SceneActor):

    def __init__(self):
        super().__init__("_TestRockerSceneActor")
        # self._enocean_target = 9

        self.mqtt_commands = []
        self.not_handled_messages: List[EnoceanMessage] = []

    def clear(self):
        self.mqtt_commands = []
        self.not_handled_messages = []

    def process_mqtt_message(self, message: MQTTMessage):
        text = message.payload
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        self.mqtt_commands.append(text)

    def name(self):
        return self.__class__.__name__

    @property
    def _logger(self):
        return _dummy_logger

    def process_enocean_message(self, message: EnoceanMessage):
        packet: RadioPacket = message.payload

        rocker_scene = self.find_rocker_scene(packet)
        if rocker_scene:
            self.process_rocker_scene(rocker_scene)
        else:
            self.not_handled_messages.append(message)


class TestBaseRockerSceneMqttCommand(unittest.TestCase):

    def setUp(self):
        self.device = _TestRockerSceneActor()

        self.device.set_config({
            device.CONFKEY_ENOCEAN_SENDER: 9,
            device.CONFKEY_ENOCEAN_TARGET: 99999,
            device.CONFKEY_MQTT_CHANNEL_CMD: "dummy-cmd",
            device.CONFKEY_MQTT_CHANNEL_STATE: "dummy-state",

            CONFKEY_ROCKER_SCENES: [
                {"rocker_id": 1, "rocker_key": 1, "command": "1"},
                {"rocker_id": 2, "rocker_key": 2, "command": "2"},
            ]
        })

    def test_enocean_targets(self):
        self.device._enocean_target = 9
        self.assertEqual(set(self.device.enocean_targets), {9, 1, 2})

    def test_rocker_actions(self):
        # noinspection PyShadowingNames
        device = self.device

        def prepare(press, button, sender):
            device.clear()
            rocker_action = RockerAction(press=press, button=button)
            packet = RockerSwitchTools.create_packet(action=rocker_action, sender=sender)
            message = EnoceanMessage(payload=packet, enocean_id=packet.sender_int)
            device.process_enocean_message(message)

        prepare(press=RockerPress.PRESS_LONG, button=RockerButton.ROCK1, sender=1)
        self.assertEqual(len(device.mqtt_commands), 1)
        self.assertEqual(device.mqtt_commands[0], "1")

        prepare(press=RockerPress.PRESS_SHORT, button=RockerButton.ROCK2, sender=2)
        self.assertEqual(len(device.mqtt_commands), 1)
        self.assertEqual(device.mqtt_commands[0], "2")

        prepare(press=RockerPress.PRESS_SHORT, button=RockerButton.ROCK3, sender=2)
        self.assertEqual(len(device.mqtt_commands), 0)
        self.assertEqual(len(device.not_handled_messages), 1)

        prepare(press=RockerPress.PRESS_SHORT, button=RockerButton.ROCK2, sender=3)
        self.assertEqual(len(device.mqtt_commands), 0)
        self.assertEqual(len(device.not_handled_messages), 1)

    def test_non_rocker_actions(self):
        command = Fsb61Command(type=Fsb61CommandType.CLOSE, time=288.0, sender=1)
        packet = Fsb61CommandConverter.create_packet(command)
        message = EnoceanMessage(payload=packet, enocean_id=packet.sender_int)
        self.device.process_enocean_message(message)

        self.assertEqual(len(self.device.mqtt_commands), 0)
        self.assertEqual(len(self.device.not_handled_messages), 1)
