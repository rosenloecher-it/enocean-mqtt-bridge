import logging
from typing import List
from queue import Queue, Empty

import paho.mqtt.client as mqtt

from src.config import ConfMainKey, Config
from src.constant import Constant

_logger = logging.getLogger(__name__)


class MqttConnector:

    def __init__(self, publisher):
        self._mqtt = None
        self._publisher = publisher
        self._is_connected = False

        # public callbacks
        self.on_connect = None
        self.on_disconnect = None

        self._message_queue = Queue()  # synchronized

    def open(self, config):
        host = Config.get_str(config, ConfMainKey.MQTT_HOST)
        port = Config.get_int(config, ConfMainKey.MQTT_PORT)
        protocol = Config.get_int(config, ConfMainKey.MQTT_PROTOCOL, Constant.DEFAULT_MQTT_PROTOCOL)
        keepalive = Config.get_int(config, ConfMainKey.MQTT_KEEPALIVE, Constant.DEFAULT_MQTT_KEEPALIVE)
        client_id = Config.get_str(config, ConfMainKey.MQTT_CLIENT_ID)
        ssl_ca_certs = Config.get_str(config, ConfMainKey.MQTT_SSL_CA_CERTS)
        ssl_certfile = Config.get_str(config, ConfMainKey.MQTT_SSL_CERTFILE)
        ssl_keyfile = Config.get_str(config, ConfMainKey.MQTT_SSL_KEYFILE)
        ssl_insecure = Config.get_bool(config, ConfMainKey.MQTT_SSL_INSECURE, False)
        is_ssl = ssl_ca_certs or ssl_certfile or ssl_keyfile
        user_name = Config.get_str(config, ConfMainKey.MQTT_USER_NAME)
        user_pwd = Config.get_str(config, ConfMainKey.MQTT_USER_PWD)

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

        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_disconnect = self._on_disconnect
        self._mqtt.on_message = self._on_message

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

    def get_queued_messages(self) -> List[mqtt.MQTTMessage]:
        messages = []

        while True:
            try:
                message = self._message_queue.get(block=False)
                messages.append(message)
            except Empty:
                break

        return messages

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

            _logger.info("subscripted to MQTT channels (%s)", channels)

    def _on_connect(self, mqtt_client, userdata, flags, rc):
        """MQTT callback is called when client connects to MQTT server."""
        if rc == 0:
            self._is_connected = True
            self._publisher.open(self)
            _logger.info("successfully connected to MQTT: flags=%s, rc=%s", flags, rc)
        else:
            _logger.error("connect to MQTT failed: flags=%s, rc=%s", flags, rc)

        if self.on_connect:
            self.on_connect(rc)

    def _on_disconnect(self, mqtt_client, userdata, rc):
        """MQTT callback for when the client disconnects from the MQTT server."""
        self._is_connected = False
        if rc == 0:
            _logger.info("disconnected from MQTT: rc=%s", rc)
        else:
            _logger.error("Unexpectedly disconnected from MQTT broker: rc=%s", rc)

        if self.on_disconnect:
            self.on_disconnect(rc)

    def _on_message(self, mqtt_client, userdata, message):
        """MQTT callback when a message is received from MQTT server"""
        try:
            _logger.debug('_on_message: topic="%s" payload="%s"', message.topic, message.payload)
            if message is not None:
                self._message_queue.put(message)
        except Exception as ex:
            _logger.exception(ex)
