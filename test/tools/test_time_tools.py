import datetime
import unittest

from src.tools.time_tools import TimeTools


class TestTimeTools(unittest.TestCase):

    def test_iso_tz(self):
        t1 = datetime.datetime(2022, 1, 29, 10, 1, 30, tzinfo=datetime.timezone(datetime.timedelta(seconds=3600)))
        self.assertEqual("2022-01-29T10:01:30+01:00", TimeTools.iso_tz(t1))
