import abc
from enum import Enum
from threading import Timer
from typing import Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.common.conf_device_key import ConfDeviceKey
from src.common.eep import Eep
from src.config import Config
from src.device.base.base_device import BaseDevice
from src.device.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools


class PropName(Enum):
    RSSI = "RSSI"


class BaseEnocean(BaseDevice):
    """Encapsulates Enocean basics."""

    MISSING_CONFIG_FOR_NAME = "no '{}' configured for device '{}'!"

    def __init__(self, name):
        super().__init__()

        if not name:
            raise RuntimeError("No valid name!")
        self._set_name(name)

        self._log_sent_packets = False
        self._enocean_connector = None

        self._enocean_target = None
        self._enocean_sender = None  # to distinguish between different actors

        self._eep = None  # type: Optional[Eep]

    @property
    def enocean_targets(self):
        return [self._enocean_target]

    def set_enocean_connector(self, enocean):
        self._enocean_connector = enocean

    def set_config(self, config):
        self._enocean_target = Config.get_int(config, ConfDeviceKey.ENOCEAN_TARGET, None)
        self._enocean_sender = Config.get_int(config, ConfDeviceKey.ENOCEAN_SENDER, None)
        self._log_sent_packets = Config.get_bool(config, ConfDeviceKey.LOG_SENT_PACKETS, False)

        if not self._enocean_target:
            message = self.MISSING_CONFIG_FOR_NAME.format(ConfDeviceKey.ENOCEAN_TARGET.value, self.name)
            self._logger.error(message)
            raise DeviceException(message)

    def _extract_default_radio_packet(self, message: EnoceanMessage) -> Optional[RadioPacket]:
        packet = message.payload  # type: RadioPacket
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return None
        if packet.rorg != self._eep.rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return None

        return packet

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
                if self._log_sent_packets:
                    instance._logger.debug("packet is being sent: %s", packet)

                instance._enocean_connector.send(packet)
            except Exception as ex:
                instance._logger.exception(ex)

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
