import unittest

from src.common.switch_status import SwitchStatus
from src.device.eltako.fud61_eep import Fud61Action, Fud61Command, Fud61Eep
from src.tools.pickle_tools import PickleTools
from test.setup_test import SetupTest

PACKET_STATUS_ON_100 = """
gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
a2V0X3R5cGVxA0sBWAQAAAByb3JncQRLpVgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
aW1lCnEJQwoH5AMdECsXAh9rcQqFcQtScQxYBAAAAGRhdGFxDV1xDihLpUsCS2RLAEsJSwVLGksu
S3xLAGVYCAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0tASwBlWAYAAABzdGF0dXNxEUsAWAYA
AABwYXJzZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2Nv
dW50cRVLAFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMA
AABkQm1xGUrA////WAYAAABzZW5kZXJxGl1xGyhLBUsaSy5LfGVYBQAAAGxlYXJucRyJdWIu
"""
# {'RSSI': -64, 'COM': 2, 'COM_EXT': 'Command ID 2', 'EDIM': 100, 'RMP': 0, 'EDIMR': 0, 'EDIMR_EXT': 'Absolute value',
# 'STR': 0, 'STR_EXT': 'No', 'SW': 1, 'SW_EXT': 'On'}


PACKET_STATUS_ON_33 = """
gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
a2V0X3R5cGVxA0sBWAQAAAByb3JncQRLpVgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
aW1lCnEJQwoH5AMdECwNB6j9cQqFcQtScQxYBAAAAGRhdGFxDV1xDihLpUsCSyFLAEsJSwVLGksu
S3xLAGVYCAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0s3SwBlWAYAAABzdGF0dXNxEUsAWAYA
AABwYXJzZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2Nv
dW50cRVLAFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMA
AABkQm1xGUrJ////WAYAAABzZW5kZXJxGl1xGyhLBUsaSy5LfGVYBQAAAGxlYXJucRyJdWIu
"""
# {'RSSI': -55, 'COM': 2, 'COM_EXT': 'Command ID 2', 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'EDIMR_EXT': 'Absolute value',
# 'STR': 0, 'STR_EXT': 'No', 'SW': 1, 'SW_EXT': 'On'}


PACKET_STATUS_OFF_0 = """
gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
a2V0X3R5cGVxA0sBWAQAAAByb3JncQRLpVgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
aW1lCnEJQwoH5AMdEC8QB1tlcQqFcQtScQxYBAAAAGRhdGFxDV1xDihLpUsCSwBLAEsISwVLGksu
S3xLAGVYCAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0s5SwBlWAYAAABzdGF0dXNxEUsAWAYA
AABwYXJzZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2Nv
dW50cRVLAFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMA
AABkQm1xGUrH////WAYAAABzZW5kZXJxGl1xGyhLBUsaSy5LfGVYBQAAAGxlYXJucRyJdWIu
"""
# {'RSSI': -57, 'COM': 2, 'COM_EXT': 'Command ID 2', 'EDIM': 0, 'RMP': 0, 'EDIMR': 0, 'EDIMR_EXT': 'Absolute value',
# 'STR': 0, 'STR_EXT': 'No', 'SW': 0, 'SW_EXT': 'Off'}


class TestFud61Eep(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_loop(self):
        actions = [
            Fud61Action(
                command=Fud61Command.STATUS_REQUEST,
            ),
            Fud61Action(
                command=Fud61Command.DIMMING,
                switch_state=SwitchStatus.ON,
            ),
            Fud61Action(
                command=Fud61Command.DIMMING,
                switch_state=SwitchStatus.OFF,
            ),
            Fud61Action(
                command=Fud61Command.DIMMING,
                dim_state=77
            )
        ]

        for action_in in actions:
            if action_in.sender is None:
                action_in.sender = 1  # default

            packet = Fud61Eep.create_packet(action_in)
            action_out = Fud61Eep.extract_packet(packet, action_in.command)

            self.assertEqual(action_out.command, action_in.command)

            if action_in.command == Fud61Command.DIMMING:
                if action_in.switch_state is not None:
                    self.assertEqual(action_out.switch_state, action_in.switch_state)
                if action_in.dim_state is not None:
                    self.assertEqual(action_out.dim_state, action_in.dim_state)

    def test_extract_off_0(self):
        packet = PickleTools.unpickle(PACKET_STATUS_OFF_0)
        # data = Fud61Eep.get_props_from_packet(packet, Fud61Command.DIMMING)
        data = Fud61Eep.get_props_from_packet(packet)
        data.pop('LNRB', None)  # depends on enocean version
        self.assertEqual(data, {'CMD': 2, 'EDIM': 0, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 0})

    def test_extract_on_33(self):
        packet = PickleTools.unpickle(PACKET_STATUS_ON_33)
        data = Fud61Eep.get_props_from_packet(packet)
        data.pop('LNRB', None)  # depends on enocean version
        self.assertEqual(data, {'CMD': 2, 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1})

    def test_extract_on_100(self):
        packet = PickleTools.unpickle(PACKET_STATUS_ON_100)
        data = Fud61Eep.get_props_from_packet(packet)
        data.pop('LNRB', None)  # depends on enocean version
        self.assertEqual(data, {'CMD': 2, 'EDIM': 100, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1})

    def test_switch_on(self):
        action = Fud61Action(command=Fud61Command.DIMMING, switch_state=SwitchStatus.ON)
        packet = Fud61Eep.create_packet(action)

        self.assertEqual(packet.data[1], 0x02)
        self.assertEqual(packet.data[2], Fud61Eep.DEFAULT_DIM_STATE)  # 100%
        # self.assertEqual(packet.data[3], 0x00)  # dim speed not relevant
        self.assertEqual(packet.data[4], 0x09)

        pass

    def test_switch_off(self):
        action = Fud61Action(command=Fud61Command.DIMMING, switch_state=SwitchStatus.OFF)
        packet = Fud61Eep.create_packet(action)

        self.assertEqual(packet.data[1], 0x02)
        # self.assertEqual(packet.data[2], 0x02) dim speed
        # self.assertEqual(packet.data[3], 0x02)
        self.assertEqual(packet.data[4], 0x08)

        pass

    def test_learn_packet(self):
        action = Fud61Action(command=Fud61Command.DIMMING, learn=True)
        packet = Fud61Eep.create_packet(action)

        # Teach-in telegram BD3...DB0 must look like this: 0xE0, 0x40, 0x0D, 0x80
        self.assertEqual(packet.data[1], 0xE0)
        self.assertEqual(packet.data[2], 0x40)
        self.assertEqual(packet.data[3], 0x0D)
        self.assertEqual(packet.data[4], 0x80)
