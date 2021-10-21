import abc
import logging
import signal
import time

from enocean import utils as enocean_utils

from src.config import ConfMainKey
from src.enocean_connector import EnoceanConnector
from src.enocean_packet_factory import EnoceanPacketFactory


_logger = logging.getLogger(__name__)


class Runner(abc.ABC):

    def __init__(self):
        self._config = None
        self._enocean_connector = None
        self._shutdown = False

        signal.signal(signal.SIGINT, self._shutdown_gracefully)
        signal.signal(signal.SIGTERM, self._shutdown_gracefully)

    def _shutdown_gracefully(self, sig, _frame):
        _logger.info("shutdown signaled (%s)", sig)
        self._shutdown = True

    def __del__(self):
        self.close()

    def open(self, config):
        self._config = config
        # if _logger.isEnabledFor(logging.DEBUG):
        #     pretty = json.dumps(self._config, indent=4, sort_keys=True)
        #     _logger.debug("config: %s", pretty)

    def close(self):
        if self._enocean_connector is not None:  # and self._enocean.is_alive():
            self._enocean_connector.close()
            self._enocean_connector = None

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError

    def _connect_enocean(self):
        key = ConfMainKey.ENOCEAN_PORT.value
        port = self._config.get(key)
        if not port:
            raise RuntimeError("no '{}' configured!".format(key))
        self._enocean_connector = EnoceanConnector(port)
        self._enocean_connector.open()

    def _wait_for_base_id(self):
        """wait until the base id is ready"""
        time_step = 0.05
        time_counter = 0

        while not self._shutdown:
            # wait for getting the adapter id
            time.sleep(time_step)
            time_counter += time_step
            if time_counter > 30:
                raise RuntimeError("Couldn't get my own Enocean ID!?")
            base_id = self._enocean_connector.base_id
            if base_id:
                # got a base id
                EnoceanPacketFactory.set_sender_id(base_id)
                if type(base_id) == list:
                    base_id = enocean_utils.combine_hex(base_id)
                _logger.info("base_id=%s", hex(base_id))
                break
