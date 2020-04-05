import abc
import copy
import logging
from datetime import datetime
from enum import Enum
from threading import Timer

from enocean.protocol.constants import PACKET
from tzlocal import get_localzone

from src.config import Config
from src.device.conf_device_key import ConfDeviceKey
from src.constant import Constant
from src.device.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.tools import Tools


class PropName(Enum):
    RSSI = "RSSI"


class BaseDevice(abc.ABC):

    MISSING_CONFIG_FOR_NAME = "no '{}' configured for device '{}'!"

    def __init__(self, name):
        if not name:
            raise RuntimeError("No valid name!")

        self._name = name
        self._logger = logging.getLogger(self._name)
        self._config = None
        self._mqtt_publisher = None
        self._enocean = None

        self._enocean_func = None
        self._enocean_id = None
        self._enocean_rorg = None
        self._enocean_type = None
        self._enocean_direction = None
        self._enocean_command = None

        self._mqtt_channel_state = None
        self._mqtt_last_will = None
        self._mqtt_qos = None
        self._mqtt_retain = None
        self._mqtt_time_offline = None

        self._enocean_activity = None
        self._update_enocean_activity()

    @property
    def name(self):
        return self._name

    @property
    def enocean_ids(self):
        return [self._enocean_id]

    def get_mqtt_last_will_channel(self):
        """signal ensor state, outbound channel"""
        return self._mqtt_channel_state

    def get_mqtt_channel_subscriptions(self):
        """signal ensor state, outbound channel"""
        return []

    def set_mqtt_publisher(self, mqtt_publisher):
        """
        :param src.mqtt_publisher.MqttPublisher mqtt_publisher:
        """
        self._mqtt_publisher = mqtt_publisher

    def set_enocean(self, enocean):
        self._enocean = enocean

    def set_config(self, config):
        self._config = copy.deepcopy(config)

        key = ConfDeviceKey.ENOCEAN_ID
        self._enocean_id = Config.post_process_int(self._config, key, None)

        def config_int(current_value, key, default_value=None):
            if current_value is not None:
                return current_value
            config_value = Config.post_process_int(self._config, ConfDeviceKey.ENOCEAN_FUNC, None)
            if config_value is not None:
                return config_value
            return default_value

        self._enocean_func = config_int(self._enocean_func, ConfDeviceKey.ENOCEAN_FUNC)
        self._enocean_rorg = config_int(self._enocean_rorg, ConfDeviceKey.ENOCEAN_RORG)
        self._enocean_type = config_int(self._enocean_type, ConfDeviceKey.ENOCEAN_TYPE)
        self._enocean_direction = config_int(self._enocean_direction, ConfDeviceKey.ENOCEAN_DIRECTION)
        self._enocean_command = config_int(self._enocean_command, ConfDeviceKey.ENOCEAN_COMMAND)

        self._mqtt_channel_state = self._config.get(ConfDeviceKey.MQTT_CHANNEL_STATE.value)
        self._check_mqtt_settings()

        self._mqtt_last_will = Config.post_process_str(self._config, ConfDeviceKey.MQTT_LAST_WILL, None)
        self._mqtt_qos = Config.post_process_int(self._config, ConfDeviceKey.MQTT_QUALITY,
                                                 Constant.DEFAULT_MQTT_QUALITY)
        self._mqtt_retain = Config.post_process_bool(self._config, ConfDeviceKey.MQTT_RETAIN, False)
        self._mqtt_time_offline = Config.post_process_int(self._config, ConfDeviceKey.MQTT_TIME_OFFLINE, None)

    def _check_enocean_settings(self):
        if not self._enocean_id:
            message = self.MISSING_CONFIG_FOR_NAME.format(ConfDeviceKey.ENOCEAN_ID.enum, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def _check_mqtt_settings(self):
        if not self._mqtt_channel_state:
            message = self.MISSING_CONFIG_FOR_NAME.format(ConfDeviceKey.MQTT_CHANNEL_STATE.value, self._name)
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
                instance._logger.debug("sent: %s", packet)

                instance._enocean.send(packet)
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

    def process_mqtt_message(self, message):
        """

        :param src.enocean_interface.EnoceanMessage message:
        """

    def _update_enocean_activity(self):
        self._enocean_activity = self._now()

    def check_and_send_offline(self):
        if self._mqtt_time_offline is not None and self._mqtt_time_offline > 0:
            now = self._now()
            diff = (now - self._enocean_activity).total_seconds()
            if diff >= self._mqtt_time_offline:
                self._update_enocean_activity()
                self.sent_last_will_no_refresh()

    def sent_last_will_no_refresh(self):
        if self._mqtt_last_will:
            self._publish(self._mqtt_last_will)
            self._logger.warning("last will sent: missing refresh")

    def sent_last_will_disconnect(self):
        if self._mqtt_last_will:
            self._publish(self._mqtt_last_will)
            self._logger.debug("last will sent: disconnecting")

    def _publish(self, message: str):
        try:
            self._mqtt_publisher.publish(
                channel=self._mqtt_channel_state,
                message=message,
                qos=self._mqtt_qos,
                retain=self._mqtt_retain
            )
            self._logger.info("mqtt publish: {0}={1}".format(self._mqtt_channel_state, message))
        except TypeError as ex:
            raise DeviceException(ex)

    def set_last_will(self):
        if self._mqtt_last_will:
            try:
                self._mqtt_publisher.will_set(
                    channel=self._mqtt_channel_state,
                    message=self._mqtt_last_will,
                    qos=self._mqtt_qos,
                    retain=self._mqtt_retain
                )
                self._logger.info("mqtt last will: {0}={1}".format(self._mqtt_channel_state, self._mqtt_last_will))
            except TypeError as ex:
                raise DeviceException(ex)

    def get_teach_message(self):
        return None

    def send_teach_telegram(self, cli_arg):
        # NotImplementedError matchs better, but let PyCharm complain about not implemented functions.
        raise RuntimeError("No teaching implemented!")

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.now(tz=get_localzone())

    @classmethod
    def packet_type_text(cls, packet_type):
        if type(packet_type) == int:
            for e in PACKET:
                if packet_type == e:
                    return e.name
        elif type(packet_type) == PACKET:
            return packet_type.name
        return str(packet_type)
