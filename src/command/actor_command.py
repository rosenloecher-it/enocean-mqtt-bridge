import json
from enum import Enum


class ActorCommand(Enum):
    DIM = "DIM"
    LEARN = "LEARN"  # TEACH IN
    OFF = "OFF"
    ON = "ON"
    UPDATE = "UPDATE"  # trigger updated notification

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))

    @classmethod
    def parse_switch(cls, text: str):
        """
        :param str text:
        :rtype: ActorCommand
        """
        orig_text = text

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        if text:
            text = text.upper().strip()

        if text and text[0] == "{":
            text = cls._extract_json(text)

        command = cls._parse_common(text)
        if command is not None:
            return command

        if text:
            if text in ["1", "100"]:
                return ActorCommand.ON
            elif text in ["0"]:
                return ActorCommand.OFF

        raise ValueError("cannot parse to command ({})!".format(orig_text))

    @classmethod
    def _parse_common(cls, text: str):
        if text:
            if text in ["ON"]:
                return ActorCommand.ON
            elif text in ["OFF"]:
                return ActorCommand.OFF
            elif text in ["UPDATE", "REFRESH"]:
                return ActorCommand.UPDATE
            elif text in ["LEARN", "TEACH", "TEACH-IN"]:
                return ActorCommand.LEARN

        return None

    @classmethod
    def _extract_json(cls, text: str):
        data = json.loads(text)

        sections = ["command", "cmd", "state", "COMMAND", "CMD", "STATE"]
        for section in sections:
            text = data.get(section)
            if text is not None:
                break

        if text:
            text = text.strip()
        return text

    @classmethod
    def parse_dimmer(cls, text: str):
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
            text = cls._extract_json(text)

        command = cls._parse_common(text)
        if command is not None:
            return (command, None)

        if text:
            try:
                value = int(text)
                if value == 0:
                    return (ActorCommand.OFF, None)
                elif 1 <= value <= 100:
                    return (ActorCommand.DIM, value)
            except ValueError:
                pass

        raise ValueError("cannot parse to command ({})!".format(orig_text))
