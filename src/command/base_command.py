import json
from enum import Enum


class BaseCommand(Enum):
    LEARN = "LEARN"  # TEACH IN
    UPDATE = "UPDATE"  # trigger updated notification

    @classmethod
    def extract_json(cls, text: str):
        data = json.loads(text)

        sections = ["command", "cmd", "COMMAND", "CMD"]
        for section in sections:
            text = data.get(section)
            if text is not None:
                break

        if text:
            text = text.strip()
        return text
