import unittest

from src.command.switch_command import SwitchCommand


class TestSwitchCommand(unittest.TestCase):

    def test_parse(self):
        self.assertEqual(SwitchCommand.parse(" On "), SwitchCommand.ON)
        self.assertEqual(SwitchCommand.parse(" 1 "), SwitchCommand.ON)
        self.assertEqual(SwitchCommand.parse(" oFF "), SwitchCommand.OFF)
        self.assertEqual(SwitchCommand.parse(" 0 "), SwitchCommand.OFF)
        self.assertEqual(SwitchCommand.parse('{"COMMAND": " ofF "}'), SwitchCommand.OFF)
        self.assertEqual(SwitchCommand.parse('{"command": " ofF "}'), SwitchCommand.OFF)
        self.assertEqual(SwitchCommand.parse('{"cmd": " ofF "}'), SwitchCommand.OFF)

        self.assertEqual(SwitchCommand.parse(" learn "), SwitchCommand.LEARN)
        self.assertEqual(SwitchCommand.parse(" teach "), SwitchCommand.LEARN)
        self.assertEqual(SwitchCommand.parse(" teach-IN "), SwitchCommand.LEARN)
        self.assertEqual(SwitchCommand.parse(" Update "), SwitchCommand.UPDATE)
        self.assertEqual(SwitchCommand.parse(" refresh "), SwitchCommand.UPDATE)

        self.assertEqual(SwitchCommand.parse(" toggle "), SwitchCommand.TOGGLE)

        with self.assertRaises(ValueError):
            SwitchCommand.parse("onnnnn")
        with self.assertRaises(ValueError):
            SwitchCommand.parse("77")
        with self.assertRaises(ValueError):
            SwitchCommand.parse("")
        with self.assertRaises(ValueError):
            SwitchCommand.parse(None)

    def test_print(self):
        self.assertEqual(str(SwitchCommand.ON), "ON")
        self.assertEqual(repr(SwitchCommand.OFF), "SwitchCommand(OFF)")

    def test_is(self):
        self.assertEqual(SwitchCommand.ON.is_on, True)
        self.assertEqual(SwitchCommand.OFF.is_off, True)
        self.assertEqual(SwitchCommand.LEARN.is_learn, True)
        self.assertEqual(SwitchCommand.UPDATE.is_update, True)

        self.assertEqual(SwitchCommand.ON.is_off, False)
        self.assertEqual(SwitchCommand.OFF.is_on, False)
        self.assertEqual(SwitchCommand.LEARN.is_update, False)
        self.assertEqual(SwitchCommand.UPDATE.is_learn, False)
