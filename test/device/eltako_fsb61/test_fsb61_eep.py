import unittest

from src.device.eltako_fsb61.fsb61_eep import Fsb61CommandType, Fsb61Command, Fsb61CommandConverter, Fsb61State, \
    Fsb61StateConverter, Fsb61StateType
from src.tools.pickle_tools import PickleTools
from test.setup_test import SetupTest

PACKET_1 = """gASVUQAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEulSwBLKksCSwpLBUuUS/hL
6UsAZYwIb3B0aW9uYWyUXZQoSwBL/0v/S/9L/0tKSwBldS4="""

PACKET_2 = """gASVSwAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEv2SwFLBUuUS/hL6UswZYwI
b3B0aW9uYWyUXZQoSwBL/0v/S/9L/0s6SwBldS4="""

PACKET_3 = """gASVUQAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEulSwBLGksBSwpLBUuUS/hL
6UsAZYwIb3B0aW9uYWyUXZQoSwBL/0v/S/9L/0tASwBldS4="""

PACKET_4 = """gASVSwAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEv2SwBLBUuUS/hL6UsgZYwI
b3B0aW9uYWyUXZQoSwBL/0v/S/9L/0s9SwBldS4="""


PACKET_5 = """gASVSwAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEv2SwJLBUuUS/hL6UswZYwI
b3B0aW9uYWyUXZQoSwBL/0v/S/9L/0s5SwBldS4="""

PACKET_UNKNOWN_1 = """gASVVQAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEvRSwBL0Ev+SwNLA0sASwVL
lEv4S+lLAGWMCG9wdGlvbmFslF2UKEsAS/9L/0v/S/9LPUsAZXUu"""

PACKET_UNKNOWN_2 = """gASVVQAAAAAAAAB9lCiMC3BhY2tldF90eXBllEsBjARkYXRhlF2UKEvRSwBL0Ev+SwNLA0sCSwVL
lEv4S+lLAGWMCG9wdGlvbmFslF2UKEsAS/9L/0v/S/9LN0sAZXUu"""


class TestFsb61CommandConverter(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_all(self):
        commands = [
            Fsb61Command(type=Fsb61CommandType.CLOSE, time=288.0),
            Fsb61Command(type=Fsb61CommandType.LEARN),
            Fsb61Command(type=Fsb61CommandType.OPEN, time=22.0),
            Fsb61Command(type=Fsb61CommandType.STATUS_REQUEST),
            Fsb61Command(type=Fsb61CommandType.STOP),
        ]
        for command_in in commands:
            packet = Fsb61CommandConverter.create_packet(command_in)

            # print(command_in)
            # print(packet)
            # print("")

            command_out = Fsb61CommandConverter.extract_packet(packet)

            command_in.sender = command_out.sender
            command_in.rssi = command_out.rssi

            self.assertEqual(command_out, command_in)


class TestFsb61StatusConverter(unittest.TestCase):

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    def test_all(self):
        dest = 0xffffffff
        sender = 0x0594f8e9

        test_items = [
            (PACKET_1, Fsb61State(type=Fsb61StateType.CLOSED, time=4.2, destination=dest, sender=sender, rssi=-74)),
            (PACKET_2, Fsb61State(type=Fsb61StateType.OPENING, destination=dest, sender=sender, rssi=-58)),
            (PACKET_3, Fsb61State(type=Fsb61StateType.OPENED, time=2.6, destination=dest, sender=sender, rssi=-64)),
            (PACKET_4, Fsb61State(type=Fsb61StateType.STOPPED, destination=dest, sender=sender, rssi=-61)),
            (PACKET_5, Fsb61State(type=Fsb61StateType.CLOSING, destination=dest, sender=sender, rssi=-57)),
        ]
        for pickeled_packet, expected_status in test_items:
            packet = PickleTools.unpickle_packet(pickeled_packet)
            status = Fsb61StateConverter.extract_packet(packet)
            self.assertEqual(status, expected_status)

    def test_ignore_unknown(self):
        packet = PickleTools.unpickle_packet(PACKET_UNKNOWN_1)
        status = Fsb61StateConverter.extract_packet(packet)
        self.assertEqual(status.type, Fsb61StateType.UNKNOWN)

    def test_create_packet(self):
        dest = 0xffffffff
        sender = 0x0594f8e9

        items = [
            Fsb61State(type=Fsb61StateType.CLOSING, destination=dest, sender=sender, rssi=-61),
            Fsb61State(type=Fsb61StateType.OPENING, destination=dest, sender=sender, rssi=-62),
            Fsb61State(type=Fsb61StateType.STOPPED, destination=dest, sender=sender, rssi=-63),
        ]

        for predefined_status in items:
            packet = Fsb61StateConverter.create_packet(predefined_status)
            status = Fsb61StateConverter.extract_packet(packet)
            self.assertEqual(status, predefined_status)
