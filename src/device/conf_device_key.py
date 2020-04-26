from enum import Enum


class ConfDeviceKey(Enum):
    # global
    NAME = "name"

    DEVICE_CLASS = "device_class"

    ENOCEAN_TARGET = "enocean_target"
    ENOCEAN_SENDER = "enocean_sender"
    ENOCEAN_RORG = "enocean_rorg"
    ENOCEAN_FUNC = "enocean_func"
    ENOCEAN_TYPE = "enocean_type"
    ENOCEAN_DIRECTION = "enocean_direction"
    ENOCEAN_COMMAND = "enocean_command"

    MQTT_CHANNEL_STATE = "mqtt_channel_state"
    MQTT_CHANNEL_CMD = "mqtt_channel_cmd"
    MQTT_LAST_WILL = "mqtt_last_will"
    MQTT_QOS = "mqtt_quality"
    MQTT_RETAIN = "mqtt_retain"

    MQTT_CHANNEL_BUTTON_0 = "mqtt_channel_button0"
    MQTT_CHANNEL_BUTTON_1 = "mqtt_channel_button1"
    MQTT_CHANNEL_BUTTON_2 = "mqtt_channel_button2"
    MQTT_CHANNEL_BUTTON_3 = "mqtt_channel_button3"

    # mainly FFG7BDevice
    STORAGE_FILE = "storage_file"
    WRITE_SINCE_SEPARATE_ERROR = "write_since_separate_error"
    WRITE_SINCE = "write_since"
    RESTORE_LAST_MAX_DIFF = "restore_last_max_diff"
    TIME_OFFLINE_MSG = "mqtt_time_offline"

    # mainly LogDevice
    DUMP_PACKETS = "dump_packets"
    ENOCEAN_IDS = "enocean_ids"
    ENOCEAN_IDS_SKIP = "enocean_ids_skip"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)
