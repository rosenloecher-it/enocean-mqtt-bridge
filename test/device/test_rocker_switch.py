import datetime
import json
import unittest

from src.device.conf_device_key import ConfDeviceKey
from src.device.rocker_switch import RockerSwitch
from src.enocean_connector import EnoceanMessage
from src.tools.pickle_tools import PickleTools
from src.tools.rocker_switch_tools import RockerSwitchTools, RockerPress, RockerButton, RockerAction


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
            packet = PickleTools.unpickle_packet(loop_data[i][0])
            device = _MockDevice()
            extracted = device._extract_packet(packet)
            action = RockerAction(press=RockerPress.PRESS_SHORT, button=loop_data[i][1])
            expected = RockerSwitchTools.create_props(action)
            self.assertEqual(extracted, expected)

    def test_extract_release(self):
        packet = PickleTools.unpickle_packet(PACKET_RELEASE)
        device = _MockDevice()
        extracted = device._extract_packet(packet)
        action = RockerAction(press=RockerPress.RELEASE)
        expected = RockerSwitchTools.create_props(action)
        self.assertEqual(extracted, expected)

    DEFAULT_MQTT_CHANNEL = "default_mqtt_channel"

    @classmethod
    def get_test_channel(cls, action):
        return f"{action.button}_{action.press}"

    @classmethod
    def create_device_for_process_enocean_message(cls):
        device = _MockDevice()

        device._mqtt_channel_state = cls.DEFAULT_MQTT_CHANNEL

        device._mqtt_channels = {
            0: cls.get_test_channel(RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0)),
            1: cls.get_test_channel(RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)),
        }
        device._mqtt_channels_long = {
            0: cls.get_test_channel(RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0)),
            2: cls.get_test_channel(RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK2)),
        }

        return device

    @classmethod
    def simu_packet_for_process_enocean_message(cls, device: RockerSwitch, action: RockerAction):
        packet = RockerSwitchTools.create_packet(action=action, destination=0xffffffff, sender=0xffffffff)
        message = EnoceanMessage(packet, device._enocean_id)
        device.process_enocean_message(message)

    def check_messages_for_process_enocean_message(self, device: RockerSwitch, action: RockerAction, channel):
        self.assertEqual(len(device.mqtt_messages), 1)
        message = device.mqtt_messages[0]

        self.assertEqual(message[1], channel)

        data = json.loads(message[0])
        self.assertEqual(data["STATE"], action.press.value)
        self.assertEqual(data["BUTTON"], action.button.value if action.button is not None else None)  # RELEASE
        self.assertEqual(data["TIMESTAMP"], device.now.isoformat())

    def test_process_enocean_message_short(self):
        action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0)
        channel = self.get_test_channel(action)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, action, channel)

    def test_process_enocean_message_long(self):
        action = RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0)
        channel = self.get_test_channel(action)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, action, channel)

    def test_process_enocean_message_short_for_long(self):
        # only short configued
        action_long = RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK1)
        action_short = RockerAction(RockerPress.PRESS_SHORT, action_long.button)

        channel = self.get_test_channel(action_short)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action_long)

        self.check_messages_for_process_enocean_message(device, action_long, channel)

    def test_process_enocean_message_only_long(self):
        # only short configued
        action = RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK2)
        channel = self.get_test_channel(action)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, action, channel)

    def test_process_enocean_message_only_long_short_to_default(self):
        # only short configued
        action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK2)
        channel = self.DEFAULT_MQTT_CHANNEL
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, action, channel)

    def test_process_enocean_message_to_default(self):
        # only channel_state configured
        action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK3)
        channel = self.DEFAULT_MQTT_CHANNEL
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, action, channel)

    def test_process_enocean_message_release(self):
        # only channel_state configured
        action = RockerAction(RockerPress.RELEASE)
        channel = self.DEFAULT_MQTT_CHANNEL
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, action, channel)

    def test_process_enocean_message_release_with_empty_channel(self):
        # only channel_state configured
        action = RockerAction(RockerPress.RELEASE)

        device = _MockDevice()
        # do default channel!
        # device._mqtt_channel_state = ""

        device._mqtt_channels = {
            0: ConfDeviceKey.MQTT_CHANNEL_BTN_0,
            2: ConfDeviceKey.MQTT_CHANNEL_BTN_2,
        }
        device._mqtt_channels_long = {
            0: ConfDeviceKey.MQTT_CHANNEL_BTN_LONG_0,
            2: ConfDeviceKey.MQTT_CHANNEL_BTN_LONG_2,
        }

        self.simu_packet_for_process_enocean_message(device, action)

        self.assertEqual(len(device.mqtt_messages), 0)
