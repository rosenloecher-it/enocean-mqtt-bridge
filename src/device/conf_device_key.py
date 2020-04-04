from enum import Enum


class ConfDeviceKey(Enum):
    # global
    NAME = "name"

    DEVICE_CLASS = "device_class"
    ENOCEAN_ID = "enocean_id"
    MQTT_CHANNEL_STATE = "mqtt_channel_state"
    MQTT_CHANNEL_CMD = "mqtt_channel_cmd"
    MQTT_LAST_WILL = "mqtt_last_will"
    MQTT_QUALITY = "mqtt_quality"
    MQTT_RETAIN = "mqtt_retain"
    MQTT_TIME_OFFLINE = "mqtt_time_offline"

    ENOCEAN_RORG = "enocean_rorg"
    ENOCEAN_FUNC = "enocean_func"
    ENOCEAN_TYPE = "enocean_type"
    ENOCEAN_DIRECTION = "enocean_direction"
    ENOCEAN_COMMAND = "enocean_command"

    # mainly FFG7BDevice
    STORAGE_FILE = "storage_file"
    WRITE_SINCE_SEPARATE_ERROR = "write_since_separate_error"
    WRITE_SINCE = "write_since"

    # mainly LogDevice
    DUMP_PACKETS = "dump_packets"
    ENOCEAN_IDS = "enocean_ids"
    ENOCEAN_IDS_SKIP = "enocean_ids_skip"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)
