import logging
import threading
from typing import List, Optional
from queue import Queue, Empty

import paho.mqtt.client as mqtt
from jsonschema import validate


_logger = logging.getLogger(__name__)


CONFKEY_MQTT_CLIENT_ID = "mqtt_client_id"
CONFKEY_MQTT_HOST = "mqtt_host"
CONFKEY_MQTT_KEEPALIVE = "mqtt_keepalive"
CONFKEY_MQTT_PORT = "mqtt_port"
CONFKEY_MQTT_PROTOCOL = "mqtt_protocol"
CONFKEY_MQTT_SSL_CA_CERTS = "mqtt_ssl_ca_certs"
CONFKEY_MQTT_SSL_CERTFILE = "mqtt_ssl_certfile"
CONFKEY_MQTT_SSL_INSECURE = "mqtt_ssl_insecure"
CONFKEY_MQTT_SSL_KEYFILE = "mqtt_ssl_keyfile"
CONFKEY_MQTT_USER_NAME = "mqtt_user_name"
CONFKEY_MQTT_USER_PWD = "mqtt_user_pwd"


MQTT_MAIN_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_MQTT_CLIENT_ID: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_HOST: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_KEEPALIVE: {"type": "integer", "minimum": 1},
        CONFKEY_MQTT_PORT: {"type": "integer"},
        CONFKEY_MQTT_PROTOCOL: {"type": "integer", "enum": [3, 4, 5]},
        CONFKEY_MQTT_SSL_CA_CERTS: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_SSL_CERTFILE: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_SSL_INSECURE: {"type": "boolean"},
        CONFKEY_MQTT_SSL_KEYFILE: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_USER_NAME: {"type": "string", "minLength": 1},
        CONFKEY_MQTT_USER_PWD: {"type": "string"},
    },
    "required": [
        CONFKEY_MQTT_HOST,
        CONFKEY_MQTT_PORT,
    ],
}


class MqttException(Exception):
    pass


class MqttConnector:

    DEFAULT_MQTT_KEEPALIVE = 60
    DEFAULT_MQTT_PORT = 1883
    DEFAULT_MQTT_PORT_SSL = 8883
    DEFAULT_MQTT_PROTOCOL = 4  # 5==MQTTv5, default: 4==MQTTv311, 3==MQTTv31

    def __init__(self, publisher):
        self._mqtt = None
        self._publisher = publisher
        self._is_connected = False
        self._connection_error_info = None  # type: Optional[str]
        self._lock = threading.Lock()

        # public callbacks
        self.on_connect = None
        self.on_disconnect = None

        self._message_queue = Queue()  # synchronized

    def open(self, config):
        validate(instance=config, schema=MQTT_MAIN_JSONSCHEMA)

        client_id = config.get(CONFKEY_MQTT_CLIENT_ID)
        host = config[CONFKEY_MQTT_HOST]
        port = config[CONFKEY_MQTT_PORT]

        keepalive = config.get(CONFKEY_MQTT_KEEPALIVE, self.DEFAULT_MQTT_KEEPALIVE)
        protocol = config.get(CONFKEY_MQTT_PROTOCOL, self.DEFAULT_MQTT_PROTOCOL)
        ssl_ca_certs = config.get(CONFKEY_MQTT_SSL_CA_CERTS)
        ssl_certfile = config.get(CONFKEY_MQTT_SSL_CERTFILE)
        ssl_insecure = config.get(CONFKEY_MQTT_SSL_INSECURE, False)
        ssl_keyfile = config.get(CONFKEY_MQTT_SSL_KEYFILE)
        user_name = config.get(CONFKEY_MQTT_USER_NAME)
        user_pwd = config.get(CONFKEY_MQTT_USER_PWD)

        is_ssl = ssl_ca_certs or ssl_certfile or ssl_keyfile

        if not port:
            port = self.DEFAULT_MQTT_PORT_SSL if is_ssl else self.DEFAULT_MQTT_PORT

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

    def ensure_connection(self):
        """
        Check for rarely unexpected disconnects, but when happens, it's not clear how to heal. At least the loop has to be restarted.
        Best to restart the whole app. Recognise a stopped service in system log.
        """
        with self._lock:
            is_connected = self._is_connected
            connection_error_info = self._connection_error_info

        if connection_error_info:
            raise MqttException(connection_error_info)  # leads to exit => restarted by systemd
        if not is_connected:
            raise MqttException("MQTT is not connected!")

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

    def _on_connect(self, _mqtt_client, _userdata, _flags, rc):
        """MQTT callback is called when client connects to MQTT server."""
        if rc == 0:
            with self._lock:
                self._is_connected = True
            _logger.debug("connected")
        else:
            connection_error_info = f"MQTT connection failed (#{rc}: {mqtt.error_string(rc)})!"
            _logger.error(connection_error_info)
            with self._lock:
                self._is_connected = False
                self._connection_error_info = connection_error_info

        if self.on_connect:
            self.on_connect(rc)

    def _on_disconnect(self, _mqtt_client, _userdata, rc):
        """MQTT callback for when the client disconnects from the MQTT server."""
        connection_error_info = None
        if rc != 0:
            connection_error_info = f"MQTT connection was lost (#{rc}: {mqtt.error_string(rc)}) => abort => restart!"

        with self._lock:
            self._is_connected = False
            if connection_error_info and not self._connection_error_info:
                self._connection_error_info = connection_error_info

        if rc == 0:
            _logger.debug("disconnected")
        else:
            _logger.error("unexpectedly disconnected: %s", connection_error_info or "???")

        if self.on_disconnect:
            self.on_disconnect(rc)

    def _on_message(self, _mqtt_client, _userdata, message):
        """MQTT callback when a message is received from MQTT server"""
        try:
            _logger.debug('_on_message: topic="%s" payload="%s"', message.topic, message.payload)
            if message is not None:
                self._message_queue.put(message)
        except Exception as ex:
            _logger.exception(ex)
