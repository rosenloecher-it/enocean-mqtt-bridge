import abc
import logging
from datetime import datetime
from enum import Enum
from threading import Timer

from enocean.protocol.constants import PACKET
from tzlocal import get_localzone

from src.config import Config
from src.device.conf_device_key import ConfDeviceKey
from src.device.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.tools import Tools


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

        self._enocean_func = None
        self._enocean_id = None
        self._enocean_rorg = None
        self._enocean_type = None
        self._enocean_direction = None
        self._enocean_command = None

    @property
    def _logger(self):
        return self._logger_by_name

    @property
    def name(self):
        return self._name

    @property
    def enocean_ids(self):
        return [self._enocean_id]

    def set_enocean_connector(self, enocean):
        self._enocean_connector = enocean

    def set_config(self, config):

        key = ConfDeviceKey.ENOCEAN_ID
        self._enocean_id = Config.get_int(config, key, None)

        def config_int(current_value, key, default_value=None):
            if current_value is not None:
                return current_value
            config_value = Config.get_int(config, ConfDeviceKey.ENOCEAN_FUNC, None)
            if config_value is not None:
                return config_value
            return default_value

        self._enocean_func = config_int(self._enocean_func, ConfDeviceKey.ENOCEAN_FUNC)
        self._enocean_rorg = config_int(self._enocean_rorg, ConfDeviceKey.ENOCEAN_RORG)
        self._enocean_type = config_int(self._enocean_type, ConfDeviceKey.ENOCEAN_TYPE)
        self._enocean_direction = config_int(self._enocean_direction, ConfDeviceKey.ENOCEAN_DIRECTION)
        self._enocean_command = config_int(self._enocean_command, ConfDeviceKey.ENOCEAN_COMMAND)

        # check setting
        if not self._enocean_id:
            message = self.MISSING_CONFIG_FOR_NAME.format(ConfDeviceKey.ENOCEAN_ID.enum, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def _extract_message(self, packet):
        """
        :param enocean.protocol.packet.RadioPacket packet:
        :rtype: dict{str, object}
        """
        if packet.packet_type == PACKET.RADIO and packet.rorg == self._enocean_rorg:
            try:
                data = Tools.extract_packet(
                    packet=packet,
                    rorg_func=self._enocean_func,
                    rorg_type=self._enocean_type,
                    direction=self._enocean_direction,
                    command=self._enocean_command
                )
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
