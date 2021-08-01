import abc
import logging
import signal

import time

import enocean

from src.config import ConfMainKey
from src.common.conf_device_key import ConfDeviceKey
from src.device.base.base_device import BaseDevice
from src.device.device_exception import DeviceException
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
        _logger.debug("config: %s", self._config)

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
        self._enocean_connector.on_receive = self._on_enocean_receive
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
                    base_id = enocean.utils.combine_hex(base_id)
                _logger.info("base_id=%s", hex(base_id))
                break

    def _create_device(self, name, config):
        if not name:
            raise DeviceException("invalid name => device skipped!")

        device_class_import = config.get(ConfDeviceKey.DEVICE_CLASS.value)

        if device_class_import in [None, "dummy"]:
            return  # skip

        try:
            device_class = self._load_class(device_class_import)
            device_instance = device_class(name)
            self._check_device_class(device_instance)
        except Exception as ex:
            _logger.exception(ex)
            raise DeviceException("cannot instantiate device: name='{}', class='{}'!".format(device_class_import, name))

        device_instance.set_config(config)

        return device_instance

    @abc.abstractmethod
    def _on_enocean_receive(self, message):
        raise NotImplementedError

    @classmethod
    def _load_class(cls, path: str) -> BaseDevice.__class__:
        delimiter = path.rfind(".")
        classname = path[delimiter + 1:len(path)]
        mod = __import__(path[0:delimiter], globals(), locals(), [classname])
        return getattr(mod, classname)

    @classmethod
    def _check_device_class(cls, device):
        if not isinstance(device, BaseDevice):
            if device:
                class_info = device.__class__.__module__ + '.' + device.__class__.__name__
            else:
                class_info = 'None'
            class_target = BaseDevice.__module__ + '.' + BaseDevice.__name__
            raise TypeError("{} is not of type {}!".format(class_info, class_target))
