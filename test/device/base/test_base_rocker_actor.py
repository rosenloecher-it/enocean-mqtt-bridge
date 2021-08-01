import unittest

from src.device.base.base_rocker_actor import RockerSwitchAction, BaseRockerActor
from src.device.rocker_switch_tools import RockerSwitchTools
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools


class _MockDevice(BaseRockerActor):

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

    def test_created_switch_packet(self):
        device = _MockDevice()
        packet = device._create_switch_packet(RockerSwitchAction.ON)

        extract = EnoceanTools.extract_props(packet=packet, eep=RockerSwitchTools.DEFAULT_EEP)

        self.assertEqual(extract, {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1})
