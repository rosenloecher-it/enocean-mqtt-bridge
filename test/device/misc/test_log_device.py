import unittest

from src.common.eep import Eep
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class TestBaseDeviceExtractProps(unittest.TestCase):
    pass


PACKET_FT55_11P = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9kswS/5L8Ev4SwJLMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sqSwBldS4="""

PACKET_FT55_11L = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ksAS/5L8Ev4SwJLIGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sqSwBldS4="""

PACKET_FT55_21P = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ksQS/5L8Ev4SwJLMGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sqSwBldS4="""

PACKET_FT55_21L = """gAN9cQAoWAsAAABwYWNrZXRfdHlwZXEBSwFYBAAAAGRhdGFxAl1xAyhL9ksAS/5L8Ev4SwJLIGVY
CAAAAG9wdGlvbmFscQRdcQUoSwBL/0v/S/9L/0sqSwBldS4="""


class TestSnifferSamples(unittest.TestCase):

    def test_ft55(self):
        packet = PickleTools.unpickle_packet(PACKET_FT55_21L)

        # f6-02-02
        eep = Eep(rorg=0xf6, func=0x02, type=0x02)

        data = EnoceanTools.extract_props(packet, eep)
        self.assertTrue(data)
        # print(data)
