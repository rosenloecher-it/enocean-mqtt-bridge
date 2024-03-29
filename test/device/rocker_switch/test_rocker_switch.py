import datetime
import unittest

from src.device.base.device import CONFKEY_ENOCEAN_TARGET
from src.device.rocker_switch.rocker_switch import RockerSwitch, CONFKEY_MQTT_CHANNEL_BTN_0, CONFKEY_MQTT_CHANNEL_BTN_1, \
    CONFKEY_MQTT_CHANNEL_BTN_LONG_0, CONFKEY_MQTT_CHANNEL_BTN_LONG_2, CONFKEY_MQTT_CHANNEL_BTN_2
from src.device.rocker_switch.rocker_switch_tools import RockerSwitchTools, RockerPress, RockerButton, RockerAction
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class _MockDevice(RockerSwitch):

    def __init__(self):
        self.now = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=datetime.timezone.utc)

        super().__init__("_MockDevice")

        self._enocean_target = 0x23232323

        self.mqtt_messages = []
        self.packets = []

    def clear(self):
        self.mqtt_messages = []
        self.packets = []

    def _now(self):
        return self.now

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)

    def _publish_mqtt(self, payload: str, mqtt_channel: str = None):
        self.mqtt_messages.append((payload, mqtt_channel))


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
            extracted = EnoceanTools.extract_packet_props(packet, device._eep)
            action = RockerAction(press=RockerPress.PRESS_SHORT, button=loop_data[i][1])
            expected = RockerSwitchTools.create_props(action)
            self.assertEqual(extracted, expected)

    def test_extract_release(self):
        packet = PickleTools.unpickle_packet(PACKET_RELEASE)
        device = _MockDevice()
        extracted = EnoceanTools.extract_packet_props(packet, device._eep)
        action = RockerAction(press=RockerPress.RELEASE)
        expected = RockerSwitchTools.create_props(action)
        self.assertEqual(extracted, expected)

    DEFAULT_MQTT_CHANNEL = "default_mqtt_channel"

    @classmethod
    def get_test_channel(cls, action):
        return {
            "topic": f"topic_{action.button}",
            "payload": f"payload_{action.press}",
        }

    @classmethod
    def create_device_for_process_enocean_message(cls):
        device = _MockDevice()

        device.set_config({
            CONFKEY_ENOCEAN_TARGET: 1001,

            # CONFKEY_ENOCEAN_SENDER: 123,

            CONFKEY_MQTT_CHANNEL_BTN_0: cls.get_test_channel(RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0)),
            CONFKEY_MQTT_CHANNEL_BTN_1: cls.get_test_channel(RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)),
            CONFKEY_MQTT_CHANNEL_BTN_LONG_0: cls.get_test_channel(RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0)),
            CONFKEY_MQTT_CHANNEL_BTN_LONG_2: cls.get_test_channel(RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK2)),
        })

        return device

    @classmethod
    def simu_packet_for_process_enocean_message(cls, device: RockerSwitch, action: RockerAction):
        packet = RockerSwitchTools.create_packet(action=action, destination=0xffffffff, sender=0xffffffff)
        message = EnoceanMessage(packet, device._enocean_target)
        device.process_enocean_message(message)

    def check_messages_for_process_enocean_message(self, device: _MockDevice, channel_config):
        self.assertEqual(len(device.mqtt_messages), 1)
        message = device.mqtt_messages[0]

        self.assertEqual(message[1], channel_config["topic"])
        self.assertEqual(message[0], channel_config["payload"])

    def test_process_enocean_message_short(self):
        action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0)
        channel_config = self.get_test_channel(action)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, channel_config)

    def test_process_enocean_message_long(self):
        action = RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0)
        channel_config = self.get_test_channel(action)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, channel_config)

    def test_process_enocean_message_short_for_long(self):
        # only short configued
        action_long = RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK1)
        action_short = RockerAction(RockerPress.PRESS_SHORT, action_long.button)

        channel_config = self.get_test_channel(action_short)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action_long)

        self.check_messages_for_process_enocean_message(device, channel_config)

    def test_process_enocean_message_only_long(self):
        # only short configued
        action = RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK2)
        channel_config = self.get_test_channel(action)
        device = self.create_device_for_process_enocean_message()
        self.simu_packet_for_process_enocean_message(device, action)

        self.check_messages_for_process_enocean_message(device, channel_config)

    def test_process_enocean_message_release_with_empty_channel(self):
        # only channel_state configured
        action = RockerAction(RockerPress.RELEASE)

        device = _MockDevice()
        # do default channel!
        # device._mqtt_channel_state = ""

        device._mqtt_channels = {
            0: CONFKEY_MQTT_CHANNEL_BTN_0,
            2: CONFKEY_MQTT_CHANNEL_BTN_2,
        }
        device._mqtt_channels_long = {
            0: CONFKEY_MQTT_CHANNEL_BTN_LONG_0,
            2: CONFKEY_MQTT_CHANNEL_BTN_LONG_2,
        }

        self.simu_packet_for_process_enocean_message(device, action)

        self.assertEqual(len(device.mqtt_messages), 0)
