import unittest

from src.common.eep import Eep
from src.device.base.device import Device
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools
from test.device.opening_sensor import sample_telegrams


class _TestExtractPropsEnocean(Device):
    def process_enocean_message(self, message):
        raise NotImplementedError()  # not used


class TestBaseDeviceExtractProps(unittest.TestCase):

    def setUp(self):
        self.eep = Eep(rorg=0xf6, func=0x10, type=0x00)

    def test_close(self):
        packet = PickleTools.unpickle(sample_telegrams.PACKET_ELTAKO_FFG7B_CLOSE)

        comp = {'WIN': 3, 'T21': 1, 'NU': 0}
        data = EnoceanTools.extract_packet_props(packet, self.eep)
        self.assertEqual(data, comp)

    def test_tilted(self):
        packet = PickleTools.unpickle(sample_telegrams.PACKET_ELTAKO_FFG7B_TILTED)

        comp = {'WIN': 1, 'T21': 1, 'NU': 0}
        data = EnoceanTools.extract_packet_props(packet, self.eep)
        self.assertEqual(data, comp)

    def test_open(self):
        packet = PickleTools.unpickle(sample_telegrams.PACKET_ELTAKO_FFG7B_OPEN)

        comp = {'WIN': 2, 'T21': 1, 'NU': 0}
        data = EnoceanTools.extract_packet_props(packet, self.eep)
        self.assertEqual(data, comp)
