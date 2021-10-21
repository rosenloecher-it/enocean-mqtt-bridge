import logging
# noinspection PyCompatibility
import queue
from collections import namedtuple

from enocean.communicators import SerialCommunicator


_logger = logging.getLogger(__name__)


# disable verbose enocen loggers
logging.getLogger("enocean.communicators.SerialCommunicator").setLevel(logging.WARNING)


EnoceanMessage = namedtuple("EnoceanMessage", ["payload", "enocean_id"])


class EnoceanConnector:

    def __init__(self, port):
        self._port = port
        self._enocean = None
        self._cached_base_id = None

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

    def get_messages(self) -> [EnoceanMessage]:
        messages = []  # type[EnoceanMessage]
        loop = 0
        while self._enocean.is_alive() and loop < 50:
            loop += 1

            try:
                packet = self._enocean.receive.get(block=False)
            except queue.Empty:
                break  # loop untile the queue is empty...

            if hasattr(packet, "sender_int"):
                message = EnoceanMessage(payload=packet, enocean_id=packet.sender_int)
                messages.append(message)

        return messages

    @property
    def base_id(self):
        if self._cached_base_id is None and self._enocean is not None:
            self._cached_base_id = self._enocean.base_id
        return self._cached_base_id

    def send(self, packet):
        if self._enocean is not None:
            self._enocean.send(packet)
            pass
