import logging
import queue
from collections import namedtuple

from enocean.communicators import SerialCommunicator

_logger = logging.getLogger("enocean")


EnoceanMessage = namedtuple("EnoceanMessage", ["payload", "enocean_id"])


class EnoceanConnector:

    def __init__(self, port):
        self._port = port
        self._enocean = None
        self._enocean_sender = None
        self.on_receive = None  # type: callable(EnoceanMessage)

    def open(self):
        self._enocean = SerialCommunicator(self._port)
        self._enocean.start()
        _logger.debug("open")

    def close(self):
        if self._enocean is not None:  # and self._enocean.is_alive():
            self._enocean.stop()
            self._enocean = None

    def is_alive(self):
        if not self._enocean:
            return False
        return self._enocean.is_alive()

    def assure_connection(self):  # force option?
        if self._enocean is None:
            self.open()
        else:
            if not self._enocean.is_alive():
                _logger.warning("enocean is not alive - try to reopen! (may crash, restart via systemd)")
                self.close()
                self.open()

    def handle_messages(self, block: bool = False):
        loop = 0
        while self._enocean.is_alive() and loop < 50:
            loop += 1

            # Request transmitter ID, if needed
            if self._enocean_sender is None:
                self._enocean_sender = self._enocean.base_id

            # loop to empty the queue...
            try:
                # get next packet
                packet = self._enocean.receive.get(block=block)

                if hasattr(packet, "sender_int"):
                    try:
                        message = EnoceanMessage(
                            payload=packet,
                            enocean_id=packet.sender_int
                        )
                        self.on_receive(message)
                    except Exception as ex:
                        _logger.exception(ex)
                else:
                    _logger.warning("packet without sender_int?!\n%s", packet)

                continue

            except queue.Empty:
                break

    @property
    def base_id(self):
        return None if self._enocean is None else self._enocean.base_id

    def send(self, packet):
        if self._enocean is not None:
            self._enocean.send(packet)
            pass
