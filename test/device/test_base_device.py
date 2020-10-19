import unittest

from src.device.base_device import BaseDevice
from src.eep import Eep
from src.tools.pickle_tools import PickleTools

PACKET_WIN_CLOSE = """
    gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
    a2V0X3R5cGVxA0sBWAQAAAByb3JncQRL9lgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
    Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
    aW1lCnEJQwoH5AMIEBMJB9fmcQqFcQtScQxYBAAAAGRhdGFxDV1xDihL9kvwSwVLh0uFS0pLIGVY
    CAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0tKSwBlWAYAAABzdGF0dXNxEUsgWAYAAABwYXJz
    ZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2NvdW50cRVL
    AFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMAAABkQm1x
    GUq2////WAYAAABzZW5kZXJxGl1xGyhLBUuHS4VLSmVYBQAAAGxlYXJucRyIdWIu
"""

PACKET_WIN_TILTED = """
    gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
    a2V0X3R5cGVxA0sBWAQAAAByb3JncQRL9lgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
    Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
    aW1lCnEJQwoH5AMIFBQSAtgpcQqFcQtScQxYBAAAAGRhdGFxDV1xDihL9kvQSwVLh0uFS0pLIGVY
    CAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0s6SwBlWAYAAABzdGF0dXNxEUsgWAYAAABwYXJz
    ZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2NvdW50cRVL
    AFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMAAABkQm1x
    GUrG////WAYAAABzZW5kZXJxGl1xGyhLBUuHS4VLSmVYBQAAAGxlYXJucRyIdWIu
"""

PACKET_WIN_OPEN = """
    gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
    a2V0X3R5cGVxA0sBWAQAAAByb3JncQRL9lgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
    Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
    aW1lCnEJQwoH5AMIFBQWDkikcQqFcQtScQxYBAAAAGRhdGFxDV1xDihL9kvgSwVLh0uFS0pLIGVY
    CAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0tASwBlWAYAAABzdGF0dXNxEUsgWAYAAABwYXJz
    ZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2NvdW50cRVL
    AFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMAAABkQm1x
    GUrA////WAYAAABzZW5kZXJxGl1xGyhLBUuHS4VLSmVYBQAAAGxlYXJucRyIdWIu
"""


class _TestExtractPropsDevice(BaseDevice):
    def process_enocean_message(self, message):
        raise NotImplementedError()  # not used


class TestBaseDeviceExtractProps(unittest.TestCase):

    def setUp(self):
        self.device = _TestExtractPropsDevice("test")
        self.device._enocean_target = 0x0587854a
        self.device._eep = Eep(rorg=0xf6, func=0x10, type=0x00)

    def test_close(self):
        packet = PickleTools.unpickle(PACKET_WIN_CLOSE)

        comp = {'WIN': 3, 'T21': 1, 'NU': 0}
        data = self.device._extract_packet_props(packet)
        self.assertEqual(data, comp)

    def test_tilted(self):
        packet = PickleTools.unpickle(PACKET_WIN_TILTED)

        comp = {'WIN': 1, 'T21': 1, 'NU': 0}
        data = self.device._extract_packet_props(packet)
        self.assertEqual(data, comp)

    def test_open(self):
        packet = PickleTools.unpickle(PACKET_WIN_OPEN)

        comp = {'WIN': 2, 'T21': 1, 'NU': 0}
        data = self.device._extract_packet_props(packet)
        self.assertEqual(data, comp)
