import datetime
import json

from src.tools.time_tools import TimeTools


class JsonTools:

    @classmethod
    def _default_json_serial(cls, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime.datetime):
            return TimeTools.iso_tz(obj)
        elif isinstance(obj, datetime.date):
            return obj.isoformat()

        raise TypeError(f"Type '{type(obj)}' is not JSON serializable!")

    @classmethod
    def dumps(cls, data, sort_keys=True, indent=None) -> str:
        return json.dumps(data, indent=indent, sort_keys=sort_keys, default=cls._default_json_serial)
