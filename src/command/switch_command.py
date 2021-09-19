from enum import Enum

from src.command.base_command import BaseCommand


class SwitchCommand(Enum):
    LEARN = BaseCommand.LEARN.value
    UPDATE = BaseCommand.UPDATE.value  # trigger updated notification

    OFF = "OFF"
    ON = "ON"

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))

    @property
    def command_text(self):
        return str(self)

    @property
    def is_on(self):
        return self == self.ON

    @property
    def is_on_or_off(self):
        return self == self.OFF or self == self.ON

    @property
    def is_off(self):
        return self == self.OFF

    @property
    def is_learn(self):
        return self == self.LEARN

    @property
    def is_update(self):
        return self == self.UPDATE

    @classmethod
    def parse(cls, text: str):
        """
        :param str text:
        :rtype: SwitchCommand
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
                command = SwitchCommand.ON
            elif text in ["OFF"]:
                command = SwitchCommand.OFF
            elif text in ["UPDATE", "REFRESH", "QUERY"]:
                command = SwitchCommand.UPDATE
            elif text in ["LEARN", "TEACH", "TEACH-IN"]:
                command = SwitchCommand.LEARN
            elif text in ["1", "100"]:
                return SwitchCommand.ON
            elif text in ["0"]:
                return SwitchCommand.OFF

        if command is None:
            raise ValueError("cannot parse to command ({})!".format(orig_text))

        return command
