import unittest

from src.device.fud61_device import Fud61Device, SwitchAction
from src.tools import Tools

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


class _MockDevice(Fud61Device):

    def __init__(self):
        super().__init__("mock")

        self._enocean_id = 0xffffffff

        self._storage.load()

    def proceed_enocean(self, message):
        raise NotImplementedError()  # not used


class TestBaseDeviceExtractProps(unittest.TestCase):

    def test_extract_off_0(self):
        packet = Tools.unpickle(PACKET_STATUS_OFF_0)
        device = _MockDevice()
        data = device._extract_message(packet)
        print(data)

    def test_extract_on_33(self):
        packet = Tools.unpickle(PACKET_STATUS_ON_33)
        device = _MockDevice()
        data = device._extract_message(packet)
        print(data)

    def test_extract_on_100(self):
        packet = Tools.unpickle(PACKET_STATUS_ON_100)
        device = _MockDevice()
        data = device._extract_message(packet)
        print(data)

    def test_created_packet(self):
        device = _MockDevice()
        packet = device._create_switch_packet(SwitchAction.ON)

        extract = Tools.extract_packet(
            packet=packet,
            rorg_func=device._switch_func,
            rorg_type=device._switch_type,
            direction=device._switch_direction,
            command=device._switch_command
        )

        self.assertEqual(extract, {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1})
