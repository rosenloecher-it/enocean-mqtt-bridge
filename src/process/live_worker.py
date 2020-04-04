import logging
import time
from typing import List

import paho.mqtt.client as mqtt

from src.config import ConfMainKey, ConfSectionKey
from src.constant import Constant
from src.device.base_device import BaseDevice
from src.device.device_exception import DeviceException
from src.mqtt_publisher import MqttPublisher
from src.process.worker import Worker

_logger = logging.getLogger("process")


class LiveWorker(Worker):

    def __init__(self):
        super().__init__()

        self._enocean_ids = {}  # type: dict[int, List[BaseDevice]]
        self._mqtt_channels = {}  # type: dict[str, BaseDevice]

        self._mqtt_publisher = MqttPublisher()

        self._mqtt = None

    def run(self):
        self._init_devices()
        self._connect_mqtt()
        self._connect_enocean()

        # TODO better
        for id, devices in self._enocean_ids.items():
            for device in devices:
                device.set_enocean(self._enocean)

        self._loop()

    def close(self):
        super().close()

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

    def _loop(self):
        time_step = 0.05
        time_wait_for_refresh = 0
        time_check_offline = 0

        try:
            while not self._shutdown:

                # TODO check for mqtt connection loss

                if time_wait_for_refresh >= 30:
                    time_wait_for_refresh = 0
                    self._enocean.assure_connection()

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

    def _check_and_send_offline(self):
        for device in self._mqtt_channels.values():
            device.check_and_send_offline()

    def _on_enocean_receive(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        listener = self._enocean_ids.get(message.enocean_id) or []

        if message.enocean_id is not None:
            none_listener = self._enocean_ids.get(None)
            if none_listener:
                listener.extend(none_listener)

        if listener:
            for device in listener:
                device.proceed_enocean(message)
        # else:
        #     _logger.debug("enocean receiver not found - cannot proceed message '%s'", message)

    def _connect_mqtt(self):
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

        self._mqtt = mqtt.Client(client_id=client_id, protocol=protocol)

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

    def _init_devices(self):
        items = self._config[ConfSectionKey.DEVICES.value]
        for name, config in items.items():
            try:
                self._init_device(name, config)
            except DeviceException as ex:
                _logger.error(ex)

    def _init_device(self, name, config):
        device_instance = self._create_device(name, config)

        device_instance.set_mqtt_publisher(self._mqtt_publisher)

        enocean_ids = device_instance.enocean_ids
        if enocean_ids is None:
            # interprete as listen to all (LogDevice)!
            enocean_ids = [None]
        for enocean_id in enocean_ids:
            former_devices = self._enocean_ids.get(enocean_id)
            if former_devices is not None:
                former_devices.append(device_instance)
            else:
                self._enocean_ids[enocean_id] = [device_instance]

        channel = device_instance.mqtt_channel
        if channel:
            # LogDevice does not send
            former_device = self._mqtt_channels.get(channel)
            if former_device is not None:
                raise DeviceException("double assignment of mqtt channel '{}' to devices '{}' and '{}'!".format(
                    former_device.name,
                    name
                ))
            self._mqtt_channels[channel] = device_instance
