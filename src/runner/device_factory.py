import logging

from src.config import CONFKEY_DEVICE_TYPE
from src.device.base.device import Device
from src.common.device_exception import DeviceException
from src.runner.device_registry import DeviceRegistry

_logger = logging.getLogger(__name__)


class DeviceFactory:

    @classmethod
    def create_device(cls, name, config):
        if not name:
            raise DeviceException("invalid name => device skipped!")

        device_type_key = config.get(CONFKEY_DEVICE_TYPE)
        if device_type_key in [None, "dummy"]:
            return None  # skip

        device_class = DeviceRegistry.get(device_type_key)
        if not device_class:
            device_class = cls._load_class(device_type_key)

        if not device_class:
            return None  # skip

        try:
            device_instance = device_class(name)
            cls._check_device_class(device_instance)
        except Exception as ex:
            _logger.exception(ex)
            raise DeviceException("cannot instantiate device: name='{}', class='{}'!".format(device_class, name))

        device_instance.set_config(config)

        return device_instance

    @classmethod
    def _load_class(cls, path: str) -> Device.__class__:
        delimiter = path.rfind(".")
        classname = path[delimiter + 1:len(path)]
        module_path = __import__(path[0:delimiter], globals(), locals(), [classname])
        return getattr(module_path, classname)

    @classmethod
    def _check_device_class(cls, device):
        if not isinstance(device, Device):
            if device:
                class_info = device.__class__.__module__ + '.' + device.__class__.__name__
            else:
                class_info = 'None'
            class_target = Device.__module__ + '.' + Device.__name__
            raise TypeError("{} is not of type {}!".format(class_info, class_target))
