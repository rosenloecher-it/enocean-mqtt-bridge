import unittest

from src.device.rocker_actor import SwitchAction, RockerActor, ActorCommand
from src.device.rocker_switch import RockerSwitch
from src.enocean_connector import EnoceanMessage
from src.tools import Tools


class _MockDevice(RockerActor):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self._enocean_id = 0xffffffff

        self.messages = []
        self.packets = []

    def _now(self):
        return self.now

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)

    def _publish_mqtt(self, message: str, mqtt_channel: str = None):
        self.messages.append(message)

    def process_mqtt_message(self, message):
        """dummy implementation of abstract method"""

    def process_enocean_message(self, message: EnoceanMessage):
        """dummy implementation of abstract method"""


class TestEltakoOnOffActor(unittest.TestCase):

    def test_extract_switch_action(self):
        self.assertEqual(RockerActor.extract_actor_command(" On "), ActorCommand.ON)
        self.assertEqual(RockerActor.extract_actor_command(" 1 "), ActorCommand.ON)
        self.assertEqual(RockerActor.extract_actor_command('{"STATE": " on "}'), ActorCommand.ON)

        self.assertEqual(RockerActor.extract_actor_command(" oFF "), ActorCommand.OFF)
        self.assertEqual(RockerActor.extract_actor_command(" 0 "), ActorCommand.OFF)
        self.assertEqual(RockerActor.extract_actor_command('{"STATE": " ofF "}'), ActorCommand.OFF)

        with self.assertRaises(ValueError):
            RockerActor.extract_actor_command("onnnnn")
        with self.assertRaises(ValueError):
            RockerActor.extract_actor_command("")
        with self.assertRaises(ValueError):
            RockerActor.extract_actor_command(None)

    def test_created_switch_packet(self):
        device = _MockDevice()
        packet = device._create_switch_packet(SwitchAction.ON)

        extract = Tools.extract_packet(
            packet=packet,
            rorg_func=RockerSwitch.DEFAULT_ENOCEAN_FUNC,
            rorg_type=RockerSwitch.DEFAULT_ENOCEAN_TYPE,
            direction=RockerSwitch.DEFAULT_ENOCEAN_DIRECTION,
            command=RockerSwitch.DEFAULT_ENOCEAN_COMMAND,
        )

        self.assertEqual(extract, {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1})
