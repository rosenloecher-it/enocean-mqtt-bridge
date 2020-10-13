import copy

from enocean.protocol.packet import RadioPacket

from src.tools.enocean_tools import EnoceanTools


class EnoceanPacketFactory:

    _sender_id = None

    @classmethod
    def set_sender_id(cls, sender_id):
        if type(sender_id) == int:
            cls._sender_id = EnoceanTools.int_to_byte_list(sender_id, 4)
        else:
            cls._sender_id = copy.deepcopy(sender_id)

    @classmethod
    def create_radio_packet(cls, rorg, rorg_func, rorg_type,
                            direction=None, command=None, destination=None, sender=None, learn=False,
                            **kwargs):

        destination_id = destination or 0xffffffff
        if type(destination_id) == int:
            destination_id = EnoceanTools.int_to_byte_list(destination_id, 4)

        sender_id = sender or cls._sender_id
        if type(sender_id) == int:
            sender_id = EnoceanTools.int_to_byte_list(sender_id, 4)

        return RadioPacket.create(
            rorg, rorg_func, rorg_type,
            direction=direction,
            command=command,
            destination=destination_id,
            sender=sender_id,
            learn=learn,
            **kwargs
        )
