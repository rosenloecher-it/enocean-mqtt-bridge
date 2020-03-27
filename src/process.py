import logging
import signal
from typing import List

import paho.mqtt.client as mqtt
import time

from src.config import ConfDeviceKey, ConfMainKey, ConfSectionKey
from src.constant import Constant
from src.device.base_device import BaseDevice
from src.device.device_exception import DeviceException
from src.enocean_connector import EnoceanConnector
from src.mqtt_publisher import MqttPublisher

_logger = logging.getLogger("process")


class Process:

    def __init__(self, config):

        self._config = config
        self._enocean_ids = {}  # type: dict[int, List[BaseDevice]]
        self._mqtt_channels = {}  # type: dict[str, BaseDevice]

        self._mqtt_publisher = MqttPublisher()

        self._mqtt = None
        self._enocean = None
        self._shutdown = False

        signal.signal(signal.SIGINT, self._shutdown_gracefully)
        signal.signal(signal.SIGTERM, self._shutdown_gracefully)

        _logger.debug("config: %s", self._config)

    def __del__(self):
        self.close()

    def _shutdown_gracefully(self, sig, frame):
        _logger.info("shutdown signaled (%s)", sig)
        self._shutdown = True

    def close(self):
        if self._enocean is not None:  # and self._enocean.is_alive():
            self._enocean.close()
            self._enocean = None

        if self._mqtt is not None:
            for channel, device in self._mqtt_channels.items():
                try:
                    device.sent_last_will_disconnect()
                except DeviceException as ex:
                    _logger.error(ex)

            self._mqtt_channels = {}
            self._mqtt_channels = {}

            self._mqtt_publisher.close()
            self._mqtt.loop_stop()
            self._mqtt.disconnect()
            self._mqtt.loop_forever()  # will block until disconnect complete
            self._mqtt = None
            _logger.debug("mqtt closed.")

    def run(self):
        time_step = 0.05
        time_wait_for_refresh = 0
        time_check_offline = 0

        try:
            while not self._shutdown:

                # TODO check mqtt

                if time_wait_for_refresh >= 600:
                    time_wait_for_refresh = 0
                    self._enocean.refresh_connection()

                self._enocean.handle_messages()

                if time_check_offline >= 5:
                    self._check_and_send_offline()

                time.sleep(time_step)
                time_wait_for_refresh += time_step
                time_check_offline += time_step

        except KeyboardInterrupt:
            # gets called without signal-handler
            _logger.debug("finishing...")
        finally:
            self.close()

    def connect_enocean(self):
        key = ConfMainKey.ENOCEAN_PORT.value
        port = self._config.get(key)
        if not port:
            raise RuntimeError("no '{}' configured!".format(key))
        self._enocean = EnoceanConnector(port)
        self._enocean.on_receive = self._on_enocean_receive
        self._enocean.open()

    def _check_and_send_offline(self):
        for device in self._mqtt_channels.values():
            device.check_and_send_offline()

    def _on_enocean_receive(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        devices = self._enocean_ids.get(message.enocean_id)
        if devices:
            for device in devices:
                device.proceed_enocean(message)
        # else:
        #     _logger.debug("enocean receiver not found - cannot proceed message '%s'", message)

    def connect_mqtt(self):
        host = self._config.get(ConfMainKey.MQTT_HOST.value)
        port = self._config.get(ConfMainKey.MQTT_PORT.value)
        protocol = self._config.get(ConfMainKey.MQTT_PROTOCOL.value)
        keepalive = self._config.get(ConfMainKey.MQTT_KEEPALIVE.value)
        client_id = self._config.get(ConfMainKey.MQTT_CLIENT_ID.value)
        ssl_ca_certs = self._config.get(ConfMainKey.MQTT_SSL_CA_CERTS.value)
        ssl_certfile = self._config.get(ConfMainKey.MQTT_SSL_CERTFILE.value)
        ssl_keyfile = self._config.get(ConfMainKey.MQTT_SSL_KEYFILE.value)
        ssl_insecure = self._config.get(ConfMainKey.MQTT_SSL_INSECURE.value)
        is_ssl = ssl_ca_certs or ssl_certfile or ssl_keyfile
        user_name = self._config.get(ConfMainKey.MQTT_USER_NAME.value)
        user_pwd = self._config.get(ConfMainKey.MQTT_USER_PWD.value)

        if not port:
            port = Constant.DEFAULT_MQTT_PORT_SSL if is_ssl else Constant.DEFAULT_MQTT_PORT

        if not host or not client_id:
            raise RuntimeError("mandatory mqtt configuration not found ({}, {})'!".format(
                ConfMainKey.MQTT_HOST.value, ConfMainKey.MQTT_CLIENT_ID.value
            ))

        self._mqtt = mqtt.Client(client_id=client_id, protocol = protocol)

        if is_ssl:
            self._mqtt.tls_set(ca_certs=ssl_ca_certs, certfile=ssl_certfile, keyfile=ssl_keyfile)
            if ssl_insecure:
                _logger.info("disabling SSL certificate verification")
                self._mqtt.tls_insecure_set(True)

        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_disconnect = self._on_mqtt_disconnect
        self._mqtt.on_message = self._on_mqtt_message
        self._mqtt.on_publish = self._on_mqtt_publish

        self._mqtt_publisher.set_mqtt(self._mqtt)

        for channel, device in self._mqtt_channels.items():
            try:
                device.set_last_will()
            except DeviceException as ex:
                _logger.error(ex)

        if user_name or user_pwd:
            self._mqtt.username_pw_set(user_name, user_pwd)
        self._mqtt.connect_async(host, port=port, keepalive=keepalive)
        self._mqtt.loop_start()

        self._mqtt_publisher.open()

    @classmethod
    def _on_mqtt_connect(self, mqtt_client, userdata, flags, rc):
        """MQTT callback is called when client connects to MQTT server."""
        if rc == 0:
            _logger.info("successfully connected to MQTT: flags=%s, rc=%s", flags, rc)
        else:
            _logger.error("connect to MQTT failed: flags=%s, rc=%s", flags, rc)

    @classmethod
    def _on_mqtt_disconnect(self, mqtt_client, userdata, rc):
        """MQTT callback for when the client disconnects from the MQTT server."""
        if rc == 0:
            _logger.info("disconnected from MQTT: rc=%s", rc)
        else:
            _logger.error("Unexpectedly disconnected from MQTT broker: rc=%s", rc)

    @classmethod
    def _on_mqtt_message(self, mqtt_client, userdata, msg):
        """MQTT callback when a message is received from MQTT server"""
        _logger.info("on_mqtt_message:\n  userdata=%s\n  msg=%s", userdata, msg)
        # TODO

    @classmethod
    def _on_mqtt_publish(self, mqtt_client, userdata, mid):
        """MQTT callback is invoked when message was successfully sent to the MQTT server."""
        _logger.debug("published MQTT message %s", str(mid))

    def init_devices(self):
        items = self._config[ConfSectionKey.DEVICES.value]
        for name, config in items.items():
            try:
                self._init_device(name, config)
            except DeviceException as ex:
                _logger.error(ex)

    def _init_device(self, name, config):
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
        device_instance.set_mqtt_publisher(self._mqtt_publisher)

        enocean_id = device_instance.enocean_id
        former_devices = self._enocean_ids.get(enocean_id)
        if former_devices is not None:
            former_devices.append(device_instance)
        else:
            self._enocean_ids[enocean_id] = [device_instance]

        channel = device_instance.mqtt_channel
        former_device = self._mqtt_channels.get(channel)
        if former_device is not None:
            raise DeviceException("double assignment of mqtt channel '{}' to devices '{}' and '{}'!".format(
                former_device.name,
                name
            ))
        self._mqtt_channels[channel] = device_instance

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
