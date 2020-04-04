import unittest

import enocean
from enocean.protocol.packet import RadioPacket

from src.tools import Tools


class TestTool(unittest.TestCase):

    def test_packet_roundtrip(self):
        props_in = {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        packet_in = RadioPacket.create(
            rorg=0xf6,
            rorg_func=0x02,
            rorg_type=0x02,
            destination=Tools.int_to_byte_list(0xffffffff, 4),
            sender=Tools.int_to_byte_list(0x123455676, 4),
            learn=False,
            **props_in
        )

        text = Tools.pickle_packet(packet_in)
        packet_out = Tools.unpickle_packet(text)

        self.assertEqual(packet_out, packet_in)

    def test_int_to_byte_list(self):
        value = 0x034567af
        byte_list = Tools.int_to_byte_list(value, 4)
        result = enocean.utils.combine_hex(byte_list)
        self.assertEqual(result, value)
