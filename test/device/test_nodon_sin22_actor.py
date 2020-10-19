import unittest

from src.device.rocker_actor import StateValue
from src.device.nodon_sin22_actor import NodonSin22Actor
from src.tools.pickle_tools import PickleTools
from test.setup_test import SetupTest


class _MockDevice(NodonSin22Actor):

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


_PACKET_1_OFF = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL0ksES2FLgEsFSxlLUEuo
SwBlWAgAAABvcHRpb25hbHEEXXEFKEsAS/9L/0v/S/9LMUsAZXUu"""

_PACKET_0_ON = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL0ksES2BL5EsFSxlLUEuo
SwBlWAgAAABvcHRpb25hbHEEXXEFKEsAS/9L/0v/S/9LMEsAZXUu"""

_PACKET_1_ON = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL0ksES2FL5EsFSxlLUEuo
SwBlWAgAAABvcHRpb25hbHEEXXEFKEsAS/9L/0v/S/9LN0sAZXUu"""

_PACKET_0_OFF = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL0ksES2BLgEsFSxlLUEuo
SwBlWAgAAABvcHRpb25hbHEEXXEFKEsAS/9L/0v/S/9LOksAZXUu"""


class TestNodonSin2Actor(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_extract_0_on(self):
        packet = PickleTools.unpickle_packet(_PACKET_0_ON)

        device = _MockDevice()
        data = device._extract_packet_props(packet)

        notification = device.extract_notification(data)
        self.assertEqual(notification.channel, 0)
        self.assertEqual(notification.switch_state, StateValue.ON)

    def test_extract_0_off(self):
        packet = PickleTools.unpickle_packet(_PACKET_0_OFF)

        device = _MockDevice()
        data = device._extract_packet_props(packet)

        notification = device.extract_notification(data)
        self.assertEqual(notification.channel, 0)
        self.assertEqual(notification.switch_state, StateValue.OFF)

    def test_extract_1_on(self):
        packet = PickleTools.unpickle_packet(_PACKET_1_ON)

        device = _MockDevice()
        data = device._extract_packet_props(packet)

        notification = device.extract_notification(data)
        self.assertEqual(notification.channel, 1)
        self.assertEqual(notification.switch_state, StateValue.ON)

    def test_extract_1_off(self):
        packet = PickleTools.unpickle_packet(_PACKET_1_OFF)

        device = _MockDevice()
        data = device._extract_packet_props(packet)

        notification = device.extract_notification(data)
        self.assertEqual(notification.channel, 1)
        self.assertEqual(notification.switch_state, StateValue.OFF)
