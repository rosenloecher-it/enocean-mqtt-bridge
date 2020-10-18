import abc
from enum import Enum

from src.config import Config
from src.device.conf_device_key import ConfDeviceKey
from src.tools.device_exception import DeviceException


class _ConfigKey(Enum):
    MQTT_CHANNEL_STATE = ConfDeviceKey.MQTT_CHANNEL_STATE.value

    MQTT_LAST_WILL = ConfDeviceKey.MQTT_LAST_WILL.value
    MQTT_QOS = ConfDeviceKey.MQTT_QOS.value
    MQTT_RETAIN = ConfDeviceKey.MQTT_RETAIN.value
    TIME_OFFLINE_MSG = ConfDeviceKey.TIME_OFFLINE_MSG.value


class BaseMqtt(abc.ABC):

    DEFAULT_MQTT_QOS = 1
    DEFAULT_MQTT_KEEPALIVE = 60
    DEFAULT_MQTT_PORT = 1883
    DEFAULT_MQTT_PORT_SSL = 1883
    DEFAULT_MQTT_PROTOCOL = 4  # 5==MQTTv5, default: 4==MQTTv311, 3==MQTTv31

    def __init__(self):
        self._mqtt_channel_state = None
        self._mqtt_last_will = None
        self._mqtt_qos = None
        self._mqtt_retain = None

        self._mqtt_publisher = None

    @property
    @abc.abstractmethod
    def _logger(self):
        raise NotImplementedError()

    def set_config(self, config):
        self._set_config(config)

        # check settings
        if not self._mqtt_channel_state:
            message = self.MISSING_CONFIG_FOR_NAME.format(_ConfigKey.MQTT_CHANNEL_STATE.value, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def _set_config(self, config):

        self._mqtt_channel_state = config.get(_ConfigKey.MQTT_CHANNEL_STATE.value)

        self._mqtt_last_will = Config.get_str(config, _ConfigKey.MQTT_LAST_WILL, None)
        self._mqtt_qos = Config.get_int(config, _ConfigKey.MQTT_QOS, self.DEFAULT_MQTT_QOS)
        self._mqtt_retain = Config.get_bool(config, _ConfigKey.MQTT_RETAIN, False)

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
    def process_mqtt_message(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
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
