import unittest

import enocean
from enocean.protocol.constants import PACKET

from src.enocean_packet_factory import EnoceanPacketFactory
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools
from test.setup_test import SetupTest


class TestTool(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_packet_roundtrip(self):
        props_in = {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        packet_in = EnoceanPacketFactory.create_radio_packet(
            rorg=0xf6,
            rorg_func=0x02,
            rorg_type=0x02,
            destination=EnoceanTools.int_to_byte_list(0xffffffff, 4),
             learn=False,
            **props_in
        )

        text = PickleTools.pickle_packet(packet_in)
        packet_out = PickleTools.unpickle_packet(text)

        self.assertEqual(packet_out, packet_in)

    def test_int_to_byte_list(self):
        value = 0x034567af
        byte_list = EnoceanTools.int_to_byte_list(value, 4)
        result = enocean.utils.combine_hex(byte_list)
        self.assertEqual(result, value)

    def test_packet_type_text(self):
        self.assertEqual(EnoceanTools.extract_packet_type_text(PACKET.RADIO), "RADIO")
        self.assertEqual(EnoceanTools.extract_packet_type_text(int(PACKET.RADIO)), "RADIO")
        self.assertEqual(EnoceanTools.extract_packet_type_text(None), "None")
