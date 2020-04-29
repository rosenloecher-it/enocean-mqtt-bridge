import unittest

from src.device.eltako_on_off_actor import StateValue
from src.device.fsr61_actor import Fsr61Actor
from src.tools import Tools
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


PACKET_OFF = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ktwSwVLGksSS/5LMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0swSwBldS4="""


PACKET_ON = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ktQSwVLGksSS/5LMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0swSwBldS4="""


class TestFsr61Actor(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_extract_off(self):
        packet = Tools.unpickle_packet(PACKET_OFF)

        device = _MockDevice()
        data = device._extract_packet(packet)
        switch_state = device.extract_switch_state(data)

        self.assertEqual(switch_state, StateValue.ON)

    def test_extract_on(self):
        packet = Tools.unpickle_packet(PACKET_ON)

        device = _MockDevice()
        data = device._extract_packet(packet)
        switch_state = device.extract_switch_state(data)

        self.assertEqual(switch_state, StateValue.OFF)
