import unittest

from src.device.rocker_switch import RockerSwitch, RockerAction, RockerButton
from src.tools import Tools


class _MockDevice(RockerSwitch):

    def __init__(self):
        self.now = None

        super().__init__("mock")

        self._enocean_id = 0xffffffff

        self.messages = []
        self.packets = []

    def _now(self):
        return self.now

    def _publish_mqtt(self, message: str):
        self.messages.append(message)

    def _send_enocean_packet(self, packet, delay=0):
        self.packets.append(packet)

    def process_mqtt_message(self, message):
        """dummy implementation of abstract method"""


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

    # def test_extract_x(self):
    #     PACKET_x3 = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ksQS/5L8kukS3tLMGVY
    #                    CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sqSwBldS4="""
    #
    #     packet = Tools.unpickle_packet(PACKET_x3)
    #     device = _MockDevice()
    #     extracted = device._extract_message(packet)
    #     # expected = _MockDevice.simu_packet_props(False, 1)
    #     print(extracted)
    #     # self.assertEqual(extracted, expected)
