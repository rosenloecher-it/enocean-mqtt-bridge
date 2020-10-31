import unittest

from src.device.rocker_actor import StateValue
from src.tools.fud61_tools import Fud61Tools, Fud61Message


class TestFud61Tools(unittest.TestCase):

    def test_extract_switch_value(self):
        self.assertEqual(Fud61Tools.extract_switch_value(0), StateValue.OFF)
        self.assertEqual(Fud61Tools.extract_switch_value(1), StateValue.ON)

        self.assertEqual(Fud61Tools.extract_switch_value(2), StateValue.ERROR)
        self.assertEqual(Fud61Tools.extract_switch_value(None), StateValue.ERROR)
        self.assertEqual(Fud61Tools.extract_switch_value("nonsense"), StateValue.ERROR)

    def test_extract_dim_value(self):
        self.assertEqual(Fud61Tools.extract_dim_value(None, None), None)
        self.assertEqual(Fud61Tools.extract_dim_value(None, 0), None)

        self.assertEqual(Fud61Tools.extract_dim_value(0, 0), 0)
        self.assertEqual(Fud61Tools.extract_dim_value(81, 0), 81)

        self.assertEqual(Fud61Tools.extract_dim_value(128, 1), int(128 / 256 + 0.5))


class TestFud61Message(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(Fud61Message()), "switch=None, dim=None")
        self.assertEqual(repr(Fud61Message()), "Fud61Message(switch=None, dim=None)")
        self.assertEqual(str(Fud61Message(switch_state=StateValue.ON, dim_value=50)), "switch=ON, dim=50")
