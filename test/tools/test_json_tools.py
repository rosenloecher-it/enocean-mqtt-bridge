import unittest
from datetime import datetime, timezone, timedelta

from src.tools.json_tools import JsonTools


class TestJsonTools(unittest.TestCase):

    def test_dumps(self):

        original_data = {
            "timestamp": datetime(2022, 3, 19, 9, 55, 15, tzinfo=timezone(timedelta(seconds=3600))),
            "boolean": True,
            "integer": 456,
            "float": 1.234,
            "text": "text123",
        }
        expected_data = '{"boolean": true, "float": 1.234, "integer": 456, "text": "text123", "timestamp": "2022-03-19T09:55:15+01:00"}'

        result_data = JsonTools.dumps(original_data)

        self.assertEqual(result_data, expected_data)
