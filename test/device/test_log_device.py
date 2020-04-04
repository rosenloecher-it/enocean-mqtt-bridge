import unittest

from src.tools import Tools


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
        packet = Tools.unpickle_packet(PACKET_FT55_21L)

        # f6-02-02
        data = Tools.extract_packet(packet, 0x02, 0x02)
        print(data)

        # PACKET_FT55_11P: {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1
        # PACKET_FT55_11L: {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}
        # PACKET_FT55_12P: {'R1': 3, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        # PACKET_FT55_12L: {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}

        # PACKET_FT55_21P: {'R1': 0, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        # PACKET_FT55_21L: {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}
        # PACKET_FT55_22P: {'R1': 2, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        # PACKET_FT55_22L: {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}

    # def test_find_eep_profile(self):
    #     packet = Tools.unpickle_packet(...)
    #
    #     direction = None
    #     command = None
    #     store_extra_data = True
    #
    #     for f in range(0, 255):
    #         for t in range(0, 255):
    #             properties = packet.parse_eep(
    #                 rorg_func=f,
    #                 rorg_type=t,
    #                 direction=direction,
    #                 command=command
    #             )
    #
    #             if not properties:
    #                 continue
    #
    #             data = {}
    #             for prop_name in properties:
    #                 try:
    #                     prop = packet.parsed[prop_name]
    #
    #                     raw_value = property['raw_value']
    #                     data[prop_name] = raw_value
    #
    #                     if store_extra_data:
    #                         value = prop['value']
    #                         if value is not None and value != raw_value:
    #                             data[prop_name + "_EXT"] = value
    #                 except AttributeError:
    #                     data[prop_name] = "!?"
    #
    #             print("{:02X}-{:02X}-{:02X}\n{}\n".format(packet.rorg, f, t, data))
