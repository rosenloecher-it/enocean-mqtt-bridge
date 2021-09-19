from enum import Enum
from typing import Optional

import attr

from src.command.base_command import BaseCommand


class ShutterCommandType(Enum):
    LEARN = BaseCommand.LEARN
    UPDATE = BaseCommand.UPDATE  # trigger updated notification

    CONFIG = "CONFIG"
    STOP = "STOP"
    POSITION = "POSITION"  # %; 0 == up; 100 == down
    # OPEN_TIME
    # CLOSE_TIME


@attr.s
class ShutterCommand:
    type = attr.ib()
    value = attr.ib(default=None)  # type: int

    def __str__(self):
        if self.is_pos:
            return str(self.value)
        elif self.type:
            return str(self.type)
        else:
            return ""

    @property
    def is_pos(self):
        return self.type == ShutterCommandType.POSITION

    @property
    def is_learn(self):
        return self.type == ShutterCommandType.LEARN

    @property
    def is_update(self):
        return self.type == ShutterCommandType.UPDATE

    @classmethod
    def parse(cls, text: str):
        """
        :param str text:
        :rtype: ShutterCommand
        """
        orig_text = text

        if isinstance(text, bytes):
            text = text.decode("utf-8")
        if text:
            text = text.upper().strip()
        if text and text[0] == "{":
            text = BaseCommand.extract_json(text)

        result = None  # type: Optional[ShutterCommand]

        if text:

            if text in ["CONFIG"]:
                result = ShutterCommand(ShutterCommandType.CONFIG)
            elif text in ["DOWN", "ON", "CLOSE"]:
                result = ShutterCommand(ShutterCommandType.POSITION, 100)
            elif text in ["UP", "OFF", "OPEN"]:
                result = ShutterCommand(ShutterCommandType.POSITION, 0)
            elif text in ["UPDATE", "REFRESH", "QUERY"]:
                result = ShutterCommand(ShutterCommandType.UPDATE)
            elif text in ["LEARN", "TEACH", "TEACH-IN"]:
                result = ShutterCommand(ShutterCommandType.LEARN)
            elif text in ["STOP"]:
                result = ShutterCommand(ShutterCommandType.STOP)
            else:
                try:
                    value = int(float(text))
                    if 0 <= value <= 100:
                        result = ShutterCommand(ShutterCommandType.POSITION, value)
                    elif 0 > value:
                        result = ShutterCommand(ShutterCommandType.POSITION, 0)
                    elif 100 < value:
                        result = ShutterCommand(ShutterCommandType.POSITION, 100)
                except ValueError:
                    pass

        if not result:
            raise ValueError("cannot parse to command ({})!".format(orig_text))

        return result
