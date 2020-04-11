import logging

import paho.mqtt.client as mqtt

from src.config import ConfMainKey
from src.constant import Constant

_logger = logging.getLogger(__name__)


class MqttConnector:

    def __init__(self, publisher):
        self._mqtt = None
        self._publisher = publisher
        self._is_connected = False

        # public callbacks
        self.on_mqtt_connect = None
        self.on_mqtt_disconnect = None

    def open(self, config):
        host = config.get(ConfMainKey.MQTT_HOST.value)
        port = config.get(ConfMainKey.MQTT_PORT.value)
        protocol = config.get(ConfMainKey.MQTT_PROTOCOL.value)
        keepalive = config.get(ConfMainKey.MQTT_KEEPALIVE.value)
        client_id = config.get(ConfMainKey.MQTT_CLIENT_ID.value)
        ssl_ca_certs = config.get(ConfMainKey.MQTT_SSL_CA_CERTS.value)
        ssl_certfile = config.get(ConfMainKey.MQTT_SSL_CERTFILE.value)
        ssl_keyfile = config.get(ConfMainKey.MQTT_SSL_KEYFILE.value)
        ssl_insecure = config.get(ConfMainKey.MQTT_SSL_INSECURE.value)
        is_ssl = ssl_ca_certs or ssl_certfile or ssl_keyfile
        user_name = config.get(ConfMainKey.MQTT_USER_NAME.value)
        user_pwd = config.get(ConfMainKey.MQTT_USER_PWD.value)

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

        self.publish_stored_last_wills()

        if user_name or user_pwd:
            self._mqtt.username_pw_set(user_name, user_pwd)
        self._mqtt.connect_async(host, port=port, keepalive=keepalive)
        self._mqtt.loop_start()

    def close(self):
        if self._mqtt is not None:
            self._publisher.close()

            self._mqtt.loop_stop()
            self._mqtt.disconnect()
            self._mqtt.loop_forever()  # will block until disconnect complete
            self._mqtt = None
            _logger.debug("mqtt closed.")

    def publish(self, channel: str, message: str, qos: int = 0, retain: bool = False):
        if not self._is_connected:
            raise RuntimeError("MQTT is not connected!")

        self._mqtt.publish(
            topic=channel,
            payload=message,
            qos=qos,
            retain=retain
        )

    def publish_stored_last_wills(self):
        wills = self._publisher.export_stored_last_wills()

        for will in wills:
            self._mqtt.will_set(
                topic=will.channel,
                payload=will.message,
                qos=will.qos,
                retain=will.retain
            )

    def subscribe(self, channels):
        subs_qos = 1  # qos for subscriptions, not used, but neccessary
        subscriptions = [(s, subs_qos) for s in channels]
        if subscriptions:
            result, dummy = self._mqtt.subscribe(subscriptions)
            if result != mqtt.MQTT_ERR_SUCCESS:
                text = "could not subscripte to mqtt #{} ({})".format(result, subscriptions)
                raise RuntimeError(text)

            _logger.info("subscripted to MQTT channels")

    def _on_mqtt_connect(self, mqtt_client, userdata, flags, rc):
        """MQTT callback is called when client connects to MQTT server."""
        if rc == 0:
            self._is_connected = True
            self._publisher.open(self)
            _logger.info("successfully connected to MQTT: flags=%s, rc=%s", flags, rc)
        else:
            _logger.error("connect to MQTT failed: flags=%s, rc=%s", flags, rc)

        if self.on_mqtt_connect:
            self.on_mqtt_connect(rc)

    def _on_mqtt_disconnect(self, mqtt_client, userdata, rc):
        """MQTT callback for when the client disconnects from the MQTT server."""
        self._is_connected = False
        if rc == 0:
            _logger.info("disconnected from MQTT: rc=%s", rc)
        else:
            _logger.error("Unexpectedly disconnected from MQTT broker: rc=%s", rc)

        if self.on_mqtt_disconnect:
            self.on_mqtt_disconnect(rc)

    def _on_mqtt_message(self, mqtt_client, userdata, message):
        """MQTT callback when a message is received from MQTT server"""
        try:
            _logger.debug('on_mqtt_message: topic="%s" payload="%s"', message.topic, message.payload)

            devices = self._mqtt_channels_subscriptions.get(message.topic)
            for device in devices:
                device.process_mqtt_message(message)
        except Exception as ex:
            _logger.exception(ex)

        if self.on_mqtt_message:
            self.on_mqtt_message(message)

    @classmethod
    def _on_mqtt_publish(self, mqtt_client, userdata, mid):
        """MQTT callback is invoked when message was successfully sent to the MQTT server."""
        _logger.debug("published MQTT message %s", str(mid))
