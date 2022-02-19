import logging
from enum import Enum
from typing import Optional

from src.device.eltako.fsb61_eep import Fsb61State, Fsb61StateType


class Fsb61ShutterState(Enum):
    READY = "ready"
    NOT_CALIBRATED = "not-calibrated"


class Fsb61ShutterPosition:
    """"""

    # 0% - 90%: real driving == changing lower edge
    # 90% - 100%, within this range the position is interpreted as shutter gaps only (rolling)
    ROLLING = 90.0

    def __init__(self, device_name):
        self._name = device_name + ".shutter-position"
        self.__logger = None  # type: Optional[logging.Logger]

        self._value = None  # type: Optional[float]
        self._jumps_without_calibration = 0
        self._calibration_time = None  # type: Optional[float]

        self.time_down_driving = None  # type: Optional[float]
        self.time_down_rolling = None  # type: Optional[float]
        self.time_up_driving = None  # type: Optional[float]
        self.time_up_rolling = None  # type: Optional[float]

    @property
    def _logger(self):
        if self.__logger:
            return self.__logger

        self.__logger = logging.getLogger(self._name)
        return self.__logger

    @property
    def status(self) -> Fsb61ShutterState:
        return Fsb61ShutterState.READY if self.validate_value(self._value) else Fsb61ShutterState.NOT_CALIBRATED

    @classmethod
    def validate_value(cls, value):
        return value is not None and 0 <= value <= 100

    @property
    def jumps_without_calibration(self) -> int:
        return self._jumps_without_calibration

    @jumps_without_calibration.setter
    def jumps_without_calibration(self, value: int):
        self._jumps_without_calibration = value

    @property
    def value(self) -> Optional[float]:
        return self._value

    @value.setter
    def value(self, value: Optional[float]):
        if value is None:
            self._value = None
        else:
            try:
                float_value = float(value)
                if not self.validate_value(float_value):
                    self._logger.warning("Invalid shutter position (%s)! Must be within 0-100.", float_value)
                    float_value = None
            except ValueError:
                self._logger.warning("Invalid shutter position (%s)!", value)
                float_value = None

            self._value = float_value

    def update(self, change: Fsb61State):
        if change:
            if change.type in [Fsb61StateType.OPENED, Fsb61StateType.CLOSED]:
                change_time = (change.time or 0) * (-1 if change.type == Fsb61StateType.OPENED else 1.0)
                if self._value is None:
                    self._calibrate(change_time)
                else:
                    self._seek(change_time)
            elif change.type == Fsb61StateType.POSITION:
                if self.validate_value(change.position):
                    self._value = change.position

    def _calibrate(self, move_time: float):
        if self._calibration_time is None:
            self._calibration_time = move_time
        else:
            self._calibration_time += move_time

        if self._calibration_time >= self.time_down_rolling + self.time_down_driving:
            self._value = 100.0
            self._jumps_without_calibration = 0
            self._calibration_time = None
        elif self._calibration_time <= -1.0 * (self.time_up_rolling + self.time_up_driving):
            self._value = 0.0
            self._jumps_without_calibration = 0
            self._calibration_time = None

    def _seek(self, move_time: float):
        # special handling rolling vs driving

        if move_time > 0:
            conf_driving_time = self.time_down_driving
            conf_rolling_time = self.time_down_rolling
        else:
            conf_driving_time = self.time_up_driving
            conf_rolling_time = self.time_up_rolling

        time_representation = self.convert_position_to_time(self._value, conf_driving_time, conf_rolling_time)
        new_time_representation = time_representation + move_time
        self._value = self.convert_time_to_position(new_time_representation, conf_driving_time, conf_rolling_time)
        self._jumps_without_calibration += 1

        if new_time_representation <= 0:
            self._value = 0.0
            self._jumps_without_calibration = 0
        elif self._value >= 100:
            self._value = 100.0
            self._jumps_without_calibration = 0

    @classmethod
    def convert_position_to_time(cls, position, conf_driving_time, conf_rolling_time):
        if position < cls.ROLLING:
            time_pos = conf_driving_time * position / cls.ROLLING
        else:
            time_pos = conf_driving_time + conf_rolling_time * (position - cls.ROLLING) / (100.0 - cls.ROLLING)

        return time_pos

    @classmethod
    def convert_time_to_position(cls, time, conf_driving_time, conf_rolling_time):
        if time < 0:
            position = 0.0
        elif time > conf_driving_time + conf_rolling_time:
            position = 100.0
        elif time <= conf_driving_time:
            position = time * cls.ROLLING / conf_driving_time
        else:
            part_rolling_time = time - conf_driving_time
            position = cls.ROLLING + part_rolling_time * (100.0 - cls.ROLLING) / conf_rolling_time

        return position

    def calc_seek_time(self, start_pos, end_pos) -> float:
        if start_pos == end_pos:
            return 0

        if start_pos < end_pos:
            conf_driving_time = self.time_down_driving
            conf_rolling_time = self.time_down_rolling
        else:
            conf_driving_time = self.time_up_driving
            conf_rolling_time = self.time_up_rolling

        time_representation_start = self.convert_position_to_time(start_pos, conf_driving_time, conf_rolling_time)
        time_representation_end = self.convert_position_to_time(end_pos, conf_driving_time, conf_rolling_time)

        seek_time = round(abs(time_representation_start - time_representation_end), 1)  # precision of enocean time is 0.1s
        return seek_time
