import unittest

import enocean.utils
from enocean.protocol.constants import PACKET

from src.common.eep import Eep
from src.enocean_packet_factory import EnoceanPacketFactory
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools
from test.setup_test import SetupTest


class TestEnoceanTools(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_packet_roundtrip(self):
        props_in = {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}

        eep = Eep(rorg=0xf6, func=0x02, type=0x02)
        packet_in = EnoceanPacketFactory.create_packet(
            eep=eep,
            destination=EnoceanTools.int_to_byte_list(0xffffffff),
            learn=False,
            **props_in
        )

        text = PickleTools.pickle_packet(packet_in)
        packet_out = PickleTools.unpickle_packet(text)

        self.assertEqual(packet_out, packet_in)

    def test_int_to_byte_list(self):
        value = 0x034567af
        byte_list = EnoceanTools.int_to_byte_list(value)
        result = enocean.utils.combine_hex(byte_list)
        self.assertEqual(result, value)

    def test_packet_type_text(self):
        self.assertEqual(EnoceanTools.packet_type_to_string(PACKET.RADIO), "RADIO")
        self.assertEqual(EnoceanTools.packet_type_to_string(int(PACKET.RADIO)), "RADIO")
        self.assertEqual(EnoceanTools.packet_type_to_string(None), "None")

    # def test_analyse_unknown_packet(self):
    #     """
    #     Try to find out a concrete EEP profile by iterating over all possible values
    #     The logging output (in `venv/lib/python3.8/site-packages/enocean/protocol/eep.py`) should be disabled temporaryly.
    #     """
    #     from src.tools.pickle_tools import PickleTools
    #     from src.tools.converter import Converter
    #
    #     packet_text = "gASVUQAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEulS5dLoUsASwhLBUsiSxRL" + "\n" + \
    #                   "50sAZYwIb3B0aW9uYWyUXZQoSwBL/0v/S/9L/0s1SwBldS4="
    #     packet = PickleTools.unpickle_packet(packet_text)
    #
    #     for rorg_func in range(0, 0xff + 1):
    #         for rorg_type in range(0, 0xff + 1):
    #             eep = Eep(rorg=packet.rorg, func=rorg_func, type=rorg_type)
    #
    #             props = EnoceanTools.extract_props(packet, eep)
    #             if (props):
    #                 print("{}-{}-{}: {}".format(
    #                     Converter.to_hex_string(packet.rorg),
    #                     Converter.to_hex_string(rorg_func),
    #                     Converter.to_hex_string(rorg_type),
    #                     props
    #                 ))
