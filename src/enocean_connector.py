import logging
import queue
from collections import namedtuple

from enocean.communicators import SerialCommunicator
from enocean.protocol.constants import PACKET, RETURN_CODE

_logger = logging.getLogger("enocean")


EnoceanMessage = namedtuple("EnoceanMessage", ["payload", "enocean_id"])


class EnoceanConnector:

    def __init__(self, port):
        self._port = port
        self._enocean = None
        self._enocean_sender = None
        self.on_receive = None

    def open(self):
        self._enocean = SerialCommunicator(self._port)
        self._enocean.start()

    def close(self):
        if self._enocean is not None:  # and self._enocean.is_alive():
            self._enocean.stop()
            self._enocean = None

    def refresh_connection(self):  # TODO force

        if self._enocean is None:
            self.open()
        else:
            if not self._enocean.is_alive():
                self.close()
                self.open()

    def handle_messages(self):
        loop = 0
        while self._enocean.is_alive() and loop < 50:
            loop += 1

            # Request transmitter ID, if needed
            if self._enocean_sender is None:
                self._enocean_sender = self._enocean.base_id

            # loop to empty the queue...
            try:
                # get next packet
                packet = self._enocean.receive.get(block=True)

                # check packet type
                if packet.packet_type == PACKET.RADIO:
                    self._process_radio_packet(packet)
                elif packet.packet_type == PACKET.RESPONSE:
                    response_code = RETURN_CODE(packet.data[0])
                    _logger.debug("got response packet: {}".format(response_code.name))
                else:
                    _logger.debug("got non-RF packet: {}".format(packet))
                    continue
            except queue.Empty:
                break

    def _process_radio_packet(self, packet):
        message = EnoceanMessage(
            payload=packet,
            enocean_id=packet.sender_int
        )
        self.on_receive(message)
