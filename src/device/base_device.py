import abc
import copy
import logging
from datetime import datetime
from enum import Enum

from enocean.protocol.constants import PACKET
from tzlocal import get_localzone

from src.config import ConfDeviceKey, Config
from src.constant import Constant
from src.device.device_exception import DeviceException


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

        self._enocean_func = None
        self._enocean_id = None
        self._enocean_rorg = None
        self._enocean_type = None

        self._mqtt_channel = None
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
    def enocean_id(self):
        return self._enocean_id

    @property
    def mqtt_channel(self):
        return self._mqtt_channel

    def set_mqtt_publisher(self, mqtt_publisher):
        """
        :param src.mqtt_publisher.MqttPublisher mqtt_publisher:
        """
        self._mqtt_publisher = mqtt_publisher

    def set_config(self, config):
        self._config = copy.deepcopy(config)

        key = ConfDeviceKey.ENOCEAN_ID
        self._enocean_id = Config.post_process_int(self._config, key, None)
        if not self._enocean_id:
            message = self.MISSING_CONFIG_FOR_NAME.format(key.enum, self._name)
            self._logger.error(message)
            raise DeviceException(message)

        self._enocean_func = Config.post_process_int(self._config, ConfDeviceKey.ENOCEAN_FUNC, None)
        self._enocean_rorg = Config.post_process_int(self._config, ConfDeviceKey.ENOCEAN_RORG, None)
        self._enocean_type = Config.post_process_int(self._config, ConfDeviceKey.ENOCEAN_TYPE, None)

        if self._enocean_func is None or self._enocean_type is None or self._enocean_rorg is None:
            txt = "missing configuration '{}' or '{}' or '{}' for device '{}'!".format(
                ConfDeviceKey.ENOCEAN_FUNC.value,
                ConfDeviceKey.ENOCEAN_TYPE.value,
                ConfDeviceKey.ENOCEAN_RORG.value,
                self._name)
            raise DeviceException(txt)

        key = ConfDeviceKey.MQTT_CHANNEL.value
        self._mqtt_channel = self._config.get(key)
        if not self._mqtt_channel:
            message = self.MISSING_CONFIG_FOR_NAME.format(key, self._name)
            self._logger.error(message)
            raise DeviceException(message)

        self._mqtt_last_will = Config.post_process_str(self._config, ConfDeviceKey.MQTT_LAST_WILL, None)
        self._mqtt_qos = Config.post_process_int(self._config, ConfDeviceKey.MQTT_QUALITY,
                                                 Constant.DEFAULT_MQTT_QUALITY)
        self._mqtt_retain = Config.post_process_bool(self._config, ConfDeviceKey.MQTT_RETAIN, False)
        self._mqtt_time_offline = Config.post_process_int(self._config, ConfDeviceKey.MQTT_TIME_OFFLINE, None)

    def _extract_message(self, packet, store_extra_data=False):
        """
        :param enocean.protocol.packet.RadioPacket packet:
        :param bool store_extra_data:
        :rtype: dict{str, object}
        """

        try:
            data = {PropName.RSSI.value: packet.dBm}

            if packet.packet_type == PACKET.RADIO and packet.rorg == self._enocean_rorg:
                # TODO add "direction"!?
                properties = packet.parse_eep(self._enocean_func, self._enocean_type)
                for prop_name in properties:
                    try:
                        property = packet.parsed[prop_name]

                        raw_value = property['raw_value']
                        data[prop_name] = raw_value

                        if store_extra_data:
                            value = property['value']
                            if value is not None and value != raw_value:
                                data[prop_name + "_EXT"] = value
                    except AttributeError:
                        self._logger.warning("cannot extract")

            return data
        except AttributeError as ex:
            raise DeviceException(ex)

    @abc.abstractmethod
    def proceed_enocean(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        self._update_enocean_activity()

    def _update_enocean_activity(self):
        self._enocean_activity = self._now()

    def check_and_send_offline(self):
        if self._mqtt_time_offline is not None and self._mqtt_time_offline > 0:
            now = self._now()
            diff = (now - self._enocean_activity).total_seconds()
            if diff >= self._mqtt_time_offline:
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
                channel=self._mqtt_channel,
                message=message,
                qos=self._mqtt_qos,
                retain=self._mqtt_retain
            )
        except TypeError as ex:
            raise DeviceException(ex)

    def set_last_will(self):
        if self._mqtt_last_will:
            try:
                self._mqtt_publisher.will_set(
                    channel=self._mqtt_channel,
                    message=self._mqtt_last_will,
                    qos=self._mqtt_qos,
                    retain=self._mqtt_retain
                )
                self._logger.debug("last will set: {0}".format(self._mqtt_last_will))
            except TypeError as ex:
                raise DeviceException(ex)

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.now(tz=get_localzone())
