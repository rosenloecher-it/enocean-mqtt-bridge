from enum import Enum


class ConfDeviceKey(Enum):
    # global
    NAME = "name"

    DEVICE_CLASS = "device_class"

    ENOCEAN_TARGET = "enocean_target"
    ENOCEAN_TARGET_SWITCH = "enocean_target_switch"
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

    # mainly RockerSwitch
    MQTT_CHANNEL_RELEASE = "mqtt_channel_release"

    MQTT_CHANNEL_BTN_0 = "mqtt_channel_0"
    MQTT_CHANNEL_BTN_1 = "mqtt_channel_1"
    MQTT_CHANNEL_BTN_2 = "mqtt_channel_2"
    MQTT_CHANNEL_BTN_3 = "mqtt_channel_3"

    MQTT_CHANNEL_BTN_LONG_0 = "mqtt_channel_long_0"
    MQTT_CHANNEL_BTN_LONG_1 = "mqtt_channel_long_1"
    MQTT_CHANNEL_BTN_LONG_2 = "mqtt_channel_long_2"
    MQTT_CHANNEL_BTN_LONG_3 = "mqtt_channel_long_3"

    ACTOR_CHANNEL = "actor_channel"

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

    # mainly Fud61SimpleSwitch
    ROCKER_BUTTON_0 = "rocker_button_0"
    ROCKER_BUTTON_1 = "rocker_button_1"
    ROCKER_BUTTON_2 = "rocker_button_2"
    ROCKER_BUTTON_3 = "rocker_button_3"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)
