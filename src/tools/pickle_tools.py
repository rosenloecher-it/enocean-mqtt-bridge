import codecs

import pickle

from enocean.protocol.constants import RORG, PACKET
from enocean.protocol.packet import Packet, UTETeachInPacket, RadioPacket, ResponsePacket, EventPacket


class PickleTools:

    @classmethod
    def pickle(cls, obj):
        # sometimes errors?! use pickle_packet
        pickled = codecs.encode(pickle.dumps(obj), "base64").decode()
        return pickled

    @classmethod
    def unpickle(cls, text):
        unpickled = pickle.loads(codecs.decode(text.encode(), "base64"))
        return unpickled

    @classmethod
    def pickle_packet(cls, packet: Packet):
        if packet is None:
            return ""

        data = {
            "packet_type": packet.packet_type,
            "data": packet.data,
            "optional": packet.optional
        }
        pickled = codecs.encode(pickle.dumps(data), "base64").decode()
        return pickled

    @classmethod
    def unpickle_packet(cls, text):
        unpickled = pickle.loads(codecs.decode(text.encode(), "base64"))

        packet_type = unpickled["packet_type"]
        data = unpickled["data"]
        opt_data = unpickled["optional"]

        # copied from: enocean/protocol/packet.py
        if packet_type == PACKET.RADIO_ERP1:
            # Need to handle UTE Teach-in here, as it's a separate packet type...
            if data[0] == RORG.UTE:
                packet = UTETeachInPacket(packet_type, data, opt_data)
            else:
                packet = RadioPacket(packet_type, data, opt_data)
        elif packet_type == PACKET.RESPONSE:
            packet = ResponsePacket(packet_type, data, opt_data)
        elif packet_type == PACKET.EVENT:
            packet = EventPacket(packet_type, data, opt_data)
        else:
            packet = Packet(packet_type, data, opt_data)

        return packet
