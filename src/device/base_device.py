import abc
import logging
from datetime import datetime
from enum import Enum
from threading import Timer

from tzlocal import get_localzone

from src.config import Config
from src.device.conf_device_key import ConfDeviceKey
from src.eep import Eep
from src.enocean_connector import EnoceanMessage
from src.tools.device_exception import DeviceException
from src.tools.enocean_tools import EnoceanTools


class PropName(Enum):
    RSSI = "RSSI"


class BaseDevice(abc.ABC):
    """Encapsulates Enocean basics. A device without Enocean makes no sense in this app!"""

    MISSING_CONFIG_FOR_NAME = "no '{}' configured for device '{}'!"

    def __init__(self, name):
        if not name:
            raise RuntimeError("No valid name!")

        self._name = name
        self._logger_by_name = logging.getLogger(self._name)
        self._enocean_connector = None

        self._enocean_target = None
        self._enocean_sender = None  # to distinguish between different actors

        self._eep = None  # type: Eep

    @property
    def _logger(self):
        return self._logger_by_name

    @property
    def name(self):
        return self._name

    @property
    def enocean_targets(self):
        return [self._enocean_target]

    def set_enocean_connector(self, enocean):
        self._enocean_connector = enocean

    def set_config(self, config):
        self._enocean_target = Config.get_int(config, ConfDeviceKey.ENOCEAN_TARGET, None)
        self._enocean_sender = Config.get_int(config, ConfDeviceKey.ENOCEAN_SENDER, None)

        if not self._enocean_target:
            message = self.MISSING_CONFIG_FOR_NAME.format(ConfDeviceKey.ENOCEAN_TARGET.enum, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def _extract_packet_props(self, packet):
        """
        :param enocean.protocol.packet.RadioPacket packet:
        :rtype: dict{str, object}
        """
        if packet.rorg == self._eep.rorg:
            try:
                data = EnoceanTools.extract_props(packet=packet, eep=self._eep)
            except AttributeError as ex:
                raise DeviceException(ex)
        else:
            data = {}

        return data

    def _send_enocean_packet(self, packet, delay=0):

        instance = self

        def do_send():
            try:
                packet.build()
                instance._logger_by_name.debug("sent: %s", packet)

                instance._enocean_connector.send(packet)
            except Exception as ex:
                instance._logger_by_name.exception(ex)

        if delay < 0.001:
            do_send()
        else:
            t = Timer(delay, do_send)
            t.start()

    @abc.abstractmethod
    def process_enocean_message(self, message: EnoceanMessage):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        raise NotImplementedError()

    def get_teach_print_message(self):
        return None

    def send_teach_telegram(self, cli_arg):
        # NotImplementedError matchs better, but let PyCharm complain about not implemented functions.
        raise RuntimeError("No teaching implemented!")

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.now(tz=get_localzone())
