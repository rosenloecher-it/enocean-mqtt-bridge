import datetime
import json
import unittest

from src.device.fud61_device import Fud61Device, SwitchAction
from src.enocean_connector import EnoceanMessage
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
        self.now = None

        super().__init__("mock")

        self._enocean_id = 0xffffffff

        self.messages = []

    def _now(self):
        return self.now

    def _publish(self, message: str):
        self.messages.append(message)


class TestBaseDeviceExtractProps(unittest.TestCase):

    def test_extract_off_0(self):
        packet = Tools.unpickle(PACKET_STATUS_OFF_0)
        device = _MockDevice()
        data = device._extract_message(packet)
        self.assertEqual(data, {'COM': 2, 'EDIM': 0, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 0})

    def test_extract_on_33(self):
        packet = Tools.unpickle(PACKET_STATUS_ON_33)
        device = _MockDevice()
        data = device._extract_message(packet)
        self.assertEqual(data, {'COM': 2, 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1})

    def test_extract_on_100(self):
        packet = Tools.unpickle(PACKET_STATUS_ON_100)
        device = _MockDevice()
        data = device._extract_message(packet)
        self.assertEqual(data, {'COM': 2, 'EDIM': 100, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1})

    def test_proceed_enocean(self):
        device = _MockDevice()
        device.now = datetime.datetime(2020, 1, 1, 2, 2, 3, tzinfo=datetime.timezone.utc)
        packet = Tools.unpickle(PACKET_STATUS_ON_33)
        message = EnoceanMessage(payload=packet, enocean_id=device._enocean_id)

        device.proceed_enocean(message)

        self.assertEqual(len(device.messages), 1)
        result = json.loads(device.messages[0])

        compare = {'TIMESTAMP': '2020-01-01T02:02:03+00:00', 'STATE': 'ON', 'RSSI': -55, 'DIM': 33}
        self.assertEqual(result, compare)


    def test_created_switch_packet(self):
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
