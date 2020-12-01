from enum import Enum


class ConfMainKey(Enum):
    CONF_FILE = "conf_file"
    LOG_FILE = "log_file"
    LOG_LEVEL = "log_level"
    LOG_MAX_BYTES = "log_max_bytes"
    LOG_MAX_COUNT = "log_max_count"
    LOG_PRINT = "log_print"
    SYSTEMD = "systemd"
    TEACH = "teach"
    TEACH_XTRA = "teach_xtra"

    ENOCEAN_PORT = "enocean_port"

    MQTT_HOST = "mqtt_host"
    MQTT_PORT = "mqtt_port"
    MQTT_PROTOCOL = "mqtt_protocol"
    MQTT_CLIENT_ID = "mqtt_client_id"
    MQTT_KEEPALIVE = "mqtt_keepalive"
    MQTT_SSL_CA_CERTS = "mqtt_ssl_ca_certs"
    MQTT_SSL_CERTFILE = "mqtt_ssl_certfile"
    MQTT_SSL_INSECURE = "mqtt_ssl_insecure"
    MQTT_SSL_KEYFILE = "mqtt_ssl_keyfile"
    MQTT_USER_NAME = "mqtt_user_name"
    MQTT_USER_PWD = "mqtt_user_pwd"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)
