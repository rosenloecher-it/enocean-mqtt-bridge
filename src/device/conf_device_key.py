from enum import Enum


class ConfDeviceKey(Enum):
    NAME = "name"

    DEVICE_CLASS = "device_class"
    ENOCEAN_ID = "enocean_id"
    MQTT_CHANNEL_STATE = "mqtt_channel_state"
    MQTT_CHANNEL_CMD = "mqtt_channel_cmd"
    MQTT_LAST_WILL = "mqtt_last_will"
    MQTT_QUALITY = "mqtt_quality"
    MQTT_RETAIN = "mqtt_retain"
    MQTT_TIME_OFFLINE = "mqtt_time_offline"

    # enocean
    ENOCEAN_RORG = "enocean_rorg"
    ENOCEAN_FUNC = "enocean_func"
    ENOCEAN_TYPE = "enocean_type"
    ENOCEAN_DIRECTION = "enocean_direction"
    ENOCEAN_COMMAND = "enocean_command"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)
