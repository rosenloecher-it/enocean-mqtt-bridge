from enum import Enum

import attr

from src.command.base_command import BaseCommand


class DimmerCommandType(Enum):
    LEARN = BaseCommand.LEARN.value
    UPDATE = BaseCommand.UPDATE.value  # trigger updated notification

    DIM = "DIM"

    OFF = "OFF"
    ON = "ON"
    TOGGLE = "TOGGLE"  # toggle ON/OFF

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))


@attr.s
class DimmerCommand:
    type = attr.ib()
    value = attr.ib(default=None)  # type: int

    def __str__(self):
        if self.is_dim:
            return str(self.value)
        elif self.type:
            return str(self.type)
        else:
            return ""

    @property
    def is_dim(self):
        return self.type == DimmerCommandType.DIM and self.value is not None

    @property
    def is_on(self):
        return self.type == DimmerCommandType.ON

    @property
    def is_on_or_off(self):
        return self.type == DimmerCommandType.ON or self.type == DimmerCommandType.OFF

    @property
    def is_off(self):
        return self.type == DimmerCommandType.OFF

    @property
    def is_toggle(self):
        return self.type == DimmerCommandType.TOGGLE

    @property
    def is_learn(self):
        return self.type == DimmerCommandType.LEARN

    @property
    def is_update(self):
        return self.type == DimmerCommandType.UPDATE

    @classmethod
    def parse(cls, text: str):
        """
        :param str text:
        :rtype: (Command, Optional(int))
        """
        orig_text = text

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        if text:
            text = text.upper().strip()
        if text and text[0] == "{":
            text = BaseCommand.extract_json(text)

        command = None

        if text:
            if text in ["ON"]:
                command = DimmerCommand(DimmerCommandType.ON)
            elif text in ["OFF"]:
                command = DimmerCommand(DimmerCommandType.OFF)
            elif text in ["UPDATE", "REFRESH"]:
                command = DimmerCommand(DimmerCommandType.UPDATE)
            elif text in ["LEARN", "TEACH", "TEACH-IN"]:
                command = DimmerCommand(DimmerCommandType.LEARN)
            elif text == "TOGGLE":
                command = DimmerCommand(DimmerCommandType.TOGGLE)
            else:
                try:
                    value = int(text)
                    if value == 0:
                        return DimmerCommand(DimmerCommandType.OFF)
                    elif 1 <= value <= 100:
                        return DimmerCommand(DimmerCommandType.DIM, value)
                except ValueError:
                    pass

        if command is None:
            raise ValueError("cannot parse to command ({})!".format(orig_text))

        return command
