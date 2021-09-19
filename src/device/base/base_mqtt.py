import abc
from typing import Optional

from paho.mqtt.client import MQTTMessage

from src.common.conf_device_key import ConfDeviceKey
from src.config import Config
from src.device.base.base_device import BaseDevice
from src.device.device_exception import DeviceException


class BaseMqtt(BaseDevice):

    DEFAULT_MQTT_QOS = 1
    DEFAULT_MQTT_KEEPALIVE = 60
    DEFAULT_MQTT_PORT = 1883
    DEFAULT_MQTT_PORT_SSL = 1883
    DEFAULT_MQTT_PROTOCOL = 4  # 5==MQTTv5, default: 4==MQTTv311, 3==MQTTv31

    def __init__(self):
        super().__init__()

        self._mqtt_channel_state = None
        self._mqtt_last_will = None
        self._mqtt_qos = None
        self._mqtt_retain = None

        self._mqtt_time_offline = None  # type: Optional[int]  # seconds
        self._mqtt_last_refresh = self._now()

        self._mqtt_publisher = None

    def set_config(self, config):
        self._set_config(config)

        # check settings
        if not self._mqtt_channel_state:
            message = self.MISSING_CONFIG_FOR_NAME.format(ConfDeviceKey.MQTT_CHANNEL_STATE.value, self.name)
            self._logger.error(message)
            raise DeviceException(message)

    def _set_config(self, config):

        self._mqtt_channel_state = config.get(ConfDeviceKey.MQTT_CHANNEL_STATE.value)

        self._mqtt_last_will = Config.get_str(config, ConfDeviceKey.MQTT_LAST_WILL, None)
        self._mqtt_qos = Config.get_int(config, ConfDeviceKey.MQTT_QOS, self.DEFAULT_MQTT_QOS)
        self._mqtt_retain = Config.get_bool(config, ConfDeviceKey.MQTT_RETAIN, False)
        self._mqtt_time_offline = Config.get_int(config, ConfDeviceKey.MQTT_TIME_OFFLINE)

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

    def open_mqtt(self):
        pass

    def close_mqtt(self):
        if self._mqtt_last_will:
            self._publish_mqtt(self._mqtt_last_will)
            self._logger.debug("last will sent: disconnecting")

    def _publish_mqtt(self, message: str, mqtt_channel: str = None):
        inner_mqtt_channel = mqtt_channel or self._mqtt_channel_state
        if inner_mqtt_channel:
            self._mqtt_publisher.publish(
                channel=inner_mqtt_channel,
                message=message,
                qos=self._mqtt_qos,
                retain=self._mqtt_retain
            )
            self._logger.info("mqtt publish: {0}={1}".format(inner_mqtt_channel, message))

    @abc.abstractmethod
    def process_mqtt_message(self, message: MQTTMessage):
        raise NotImplementedError

    def set_last_will(self):
        if self._mqtt_last_will:
            self._mqtt_publisher.store_last_will(
                channel=self._mqtt_channel_state,
                message=self._mqtt_last_will,
                qos=self._mqtt_qos,
                retain=self._mqtt_retain
            )
            self._logger.info("mqtt last will: {0}={1}".format(self._mqtt_channel_state, self._mqtt_last_will))

    def _reset_offline_message_counter(self):
        """Reset offline message counter"""
        self._mqtt_last_refresh = self._now()

    def _check_and_send_offline(self):
        if self._mqtt_last_will is not None and self._mqtt_time_offline is not None \
                and self._mqtt_time_offline > 0 and self._mqtt_last_refresh is not None:
            now = self._now()
            diff = (now - self._mqtt_last_refresh).total_seconds()
            if diff >= self._mqtt_time_offline:
                self._mqtt_last_refresh = now
                self._publish_mqtt(self._mqtt_last_will)
                self._logger.warning("last will sent: missing refresh")
