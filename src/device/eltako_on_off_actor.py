import json
from enum import Enum
from typing import Optional

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.base_mqtt import BaseMqtt
from src.device.conf_device_key import ConfDeviceKey
from src.device.device_exception import DeviceException
from src.device.rocker_switch import RockerSwitch, RockerAction, RockerButton


class SwitchAction(Enum):
    ON = "on"  # press
    OFF = "off"  # press
    RELEASE = "release"


class StateValue(Enum):
    ERROR = "ERROR"
    OFF = "OFF"
    ON = "ON"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)

    @classmethod
    def is_success(cls, state):
        return state in [cls.OFF, cls.ON]


class OutputAttributes(Enum):
    RSSI = "RSSI"
    TIMESTAMP = "TIMESTAMP"
    STATE = "STATE"
    DIM = "DIM"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


class EltakoOnOffActor(BaseDevice, BaseMqtt):

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)

        self._mqtt_channel_cmd = None

    def set_config(self, config):
        BaseDevice.set_config(self, config)
        BaseMqtt.set_config(self, config)

        key = ConfDeviceKey.MQTT_CHANNEL_CMD
        self._mqtt_channel_cmd = Config.get_str(config, key)
        if not self._mqtt_channel_cmd:
            message = self.MISSING_CONFIG_FOR_NAME.format(key.value, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def get_mqtt_channel_subscriptions(self):
        """signal ensor state, outbound channel"""
        return [self._mqtt_channel_cmd]

    @classmethod
    def extract_switch_state(cls, value):
        if value == 1:
            return StateValue.ON
        elif value == 0:
            return StateValue.OFF
        else:
            return StateValue.ERROR

    def _create_message(self, switch_state: StateValue, dim_state: Optional[int], rssi: Optional[int] = None):
        data = {
            OutputAttributes.TIMESTAMP.value: self._now().isoformat(),
            OutputAttributes.STATE.value: switch_state.value
        }
        if rssi is not None:
            data[OutputAttributes.RSSI.value] = rssi
        if dim_state is not None:
            data[OutputAttributes.DIM.value] = dim_state

        json_text = json.dumps(data)
        return json_text

    def _create_switch_packet(self, action):
        # simulate rocker switch
        if action == SwitchAction.ON:
            action = RockerAction.PRESS_SINGLE
            button = RockerButton.ROCK11
        elif action == SwitchAction.OFF:
            action = RockerAction.PRESS_SINGLE
            button = RockerButton.ROCK12
        elif action == SwitchAction.RELEASE:
            action = RockerAction.RELEASE
            button = None
        else:
            raise RuntimeError()

        return RockerSwitch.simu_packet(action, button)

    @classmethod
    def extract_switch_action(cls, text: str, recusive=True) -> SwitchAction:
        if text:
            comp = str(text).upper().strip()
            if comp in ["ON", "1", "100"]:
                return SwitchAction.ON
            elif comp in ["OFF", "0"]:
                return SwitchAction.OFF
            elif recusive and comp[0] == "{":  # {"STATE": "off"}
                data = json.loads(text)
                value = data.get(OutputAttributes.STATE.value)
                return cls.extract_switch_action(value, recusive=False)

        raise ValueError()