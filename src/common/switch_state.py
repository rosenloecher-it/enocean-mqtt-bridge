from enum import Enum


class SwitchState(Enum):
    ERROR = "error"
    OFF = "off"
    ON = "on"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)
