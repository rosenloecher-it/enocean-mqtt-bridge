import logging


class Constant:
    APP_NAME = "Enocean MQTT Bridge"
    APP_DESC = "Relay messages between Enocean (USB) and MQTT"
    APP_VERSION = "0.0.1"

    DEFAULT_CONFFILE = "/etc/enocean_mqtt_bridge.conf"

    DEFAULT_LOGLEVEL = logging.INFO
    DEFAULT_LOG_MAX_BYTES = 1048576
    DEFAULT_LOG_MAX_COUNT = 10
    DEFAULT_LOG_PRINT = False
    DEFAULT_SYSTEMD = False

    DEFAULT_MQTT_PORT = 1883
    DEFAULT_MQTT_PORT_SSL = 1883
    DEFAULT_MQTT_QUALITY = 0
    DEFAULT_MQTT_KEEPALIVE = 300
