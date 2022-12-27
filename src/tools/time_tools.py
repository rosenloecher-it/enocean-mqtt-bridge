import datetime
import time

from tzlocal import get_localzone


class TimeTools:

    @classmethod
    def now(cls, no_ms=False) -> datetime.datetime:
        """overwrite/mock in test"""
        now = datetime.datetime.now(tz=get_localzone())
        if no_ms:
            now = now.replace(microsecond=0)
        return now

    @classmethod
    def diff_seconds(cls, reference: datetime.datetime):
        return (cls.now() - reference).total_seconds()

    @classmethod
    def sleep(cls, seconds: float) -> float:
        time.sleep(seconds)
        return seconds

    @classmethod
    def iso_tz(cls, value):
        return value.astimezone().isoformat()
