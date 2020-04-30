import datetime
import json
import unittest

from src.device.rocker_switch import RockerSwitch, RockerAction, RockerButton
from src.enocean_connector import EnoceanMessage
from src.tools import Tools


class _MockDevice(RockerSwitch):

    def __init__(self):
        self.now = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=datetime.timezone.utc)

        super().__init__("mock")

        self._enocean_id = 0xffffffff

        self.mqtt_messages = []
        self.packets = []

    def clear(self):
        self.mqtt_messages = []
        self.packets = []

    def _now(self):
        return self.now

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)

    def _publish_mqtt(self, message: str, mqtt_channel: str = None):
        self.mqtt_messages.append((message, mqtt_channel))


PACKET_0_PRESS = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ksQS/5L8kukS3tLMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0ssSwBldS4="""

PACKET_1_PRESS = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9kswS/5L8kukS3tLMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0ssSwBldS4="""

PACKET_2_PRESS = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ktQSwVLGksSS/5LMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0szSwBldS4="""

PACKET_3_PRESS = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ktwSwVLGksSS/5LMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sxSwBldS4="""

PACKET_RELEASE = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ksAS/5L8kukS3tLIGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sqSwBldS4="""


class TestRockerSwitch(unittest.TestCase):

    def test_extract_press(self):
        loop_data = [
            (PACKET_0_PRESS, RockerButton.ROCK0),
            (PACKET_1_PRESS, RockerButton.ROCK1),
            (PACKET_2_PRESS, RockerButton.ROCK2),
            (PACKET_3_PRESS, RockerButton.ROCK3),
        ]

        for i in range(0, 3):
            packet = Tools.unpickle_packet(loop_data[i][0])
            device = _MockDevice()
            extracted = device._extract_packet(packet)
            expected = _MockDevice.simu_packet_props(RockerAction.PRESS_SHORT, loop_data[i][1])
            self.assertEqual(extracted, expected)

    def test_extract_release(self):
        packet = Tools.unpickle_packet(PACKET_RELEASE)
        device = _MockDevice()
        extracted = device._extract_packet(packet)
        expected = _MockDevice.simu_packet_props(RockerAction.RELEASE, None)
        self.assertEqual(extracted, expected)

    DEFAULT_MQTT_CHANNEL = "default_mqtt_channel"

    @classmethod
    def get_test_channel(cls, action, button):
        return f"{button}_{action.value}"

    @classmethod
    def create_device_for_process_enocean_message(cls):
        device = _MockDevice()

        device._mqtt_channel_state = cls.DEFAULT_MQTT_CHANNEL

        device._mqtt_channels = {
            0: cls.get_test_channel(RockerAction.PRESS_SHORT, RockerButton.ROCK0),
            1: cls.get_test_channel(RockerAction.PRESS_SHORT, RockerButton.ROCK1),
        }
        device._mqtt_channels_long = {
            0: cls.get_test_channel(RockerAction.PRESS_LONG, RockerButton.ROCK0),
            2: cls.get_test_channel(RockerAction.PRESS_LONG, RockerButton.ROCK2),
        }

        return device

    @classmethod
    def simu_packet_for_process_enocean_message(cls, device, action, button):

        packet = _MockDevice.simu_packet(
            action=action, button=button,
            destination=0xffffffff, sender=0xffffffff
        )
        message = EnoceanMessage(packet, device._enocean_id)
        device.process_enocean_message(message)

    def check_messages_for_process_enocean_message(self, device, action, button, channel):
        self.assertEqual(len(device.mqtt_messages), 1)
        message = device.mqtt_messages[0]

        self.assertEqual(message[1], channel)

        data = json.loads(message[0])
        self.assertEqual(data["STATE"], action.value)
        self.assertEqual(data["BUTTON"], button.value if button is not None else None)  # in case of RELEASE
        self.assertEqual(data["TIMESTAMP"], device.now.isoformat())

    def test_process_enocean_message_short(self):
        action = RockerAction.PRESS_SHORT
        button = RockerButton.ROCK0
        channel = self.get_test_channel(action, button)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)

    def test_process_enocean_message_long(self):
        action = RockerAction.PRESS_LONG
        button = RockerButton.ROCK0
        channel = self.get_test_channel(action, button)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)

    def test_process_enocean_message_short_for_long(self):
        # only short configued
        action = RockerAction.PRESS_LONG
        button = RockerButton.ROCK1
        channel = self.get_test_channel(RockerAction.PRESS_SHORT, button)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)

    def test_process_enocean_message_only_long(self):
        # only short configued
        action = RockerAction.PRESS_LONG
        button = RockerButton.ROCK2
        channel = self.get_test_channel(action, button)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)

    def test_process_enocean_message_only_long_short_to_default(self):
        # only short configued
        action = RockerAction.PRESS_SHORT
        button = RockerButton.ROCK2
        channel = self.DEFAULT_MQTT_CHANNEL
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)

    def test_process_enocean_message_to_default(self):
        # only channel_state configured
        action = RockerAction.PRESS_SHORT
        button = RockerButton.ROCK3
        channel = self.DEFAULT_MQTT_CHANNEL
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)

    def test_process_enocean_message_release(self):
        # only channel_state configured
        action = RockerAction.RELEASE
        button = None
        channel = self.DEFAULT_MQTT_CHANNEL
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action, button)

        self.check_messages_for_process_enocean_message(device, action, button, channel)
