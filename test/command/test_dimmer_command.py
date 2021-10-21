import unittest

from src.command.dimmer_command import DimmerCommand, DimmerCommandType


class TestDimmerCommand(unittest.TestCase):

    def test_parse(self):

        self.assertEqual(DimmerCommand.parse(" On "), DimmerCommand(DimmerCommandType.ON))

        self.assertEqual(DimmerCommand.parse('{"COMMAND": " on "}'), DimmerCommand(DimmerCommandType.ON))
        self.assertEqual(DimmerCommand.parse(" oFF "), DimmerCommand(DimmerCommandType.OFF))
        self.assertEqual(DimmerCommand.parse('{"COMMAND": " ofF "}'), DimmerCommand(DimmerCommandType.OFF))
        self.assertEqual(DimmerCommand.parse(" learn "), DimmerCommand(DimmerCommandType.LEARN))
        self.assertEqual(DimmerCommand.parse(" teach "), DimmerCommand(DimmerCommandType.LEARN))
        self.assertEqual(DimmerCommand.parse(" teach-IN "), DimmerCommand(DimmerCommandType.LEARN))
        self.assertEqual(DimmerCommand.parse(" Update "), DimmerCommand(DimmerCommandType.UPDATE))
        self.assertEqual(DimmerCommand.parse(" refresh "), DimmerCommand(DimmerCommandType.UPDATE))
        self.assertEqual(DimmerCommand.parse(" toggle "), DimmerCommand(DimmerCommandType.TOGGLE))

        self.assertEqual(DimmerCommand.parse(" 1 "), DimmerCommand(DimmerCommandType.DIM, 1))
        self.assertEqual(DimmerCommand.parse(" 77 "), DimmerCommand(DimmerCommandType.DIM, 77))
        self.assertEqual(DimmerCommand.parse('{"COMMAND": " 9 "}'), DimmerCommand(DimmerCommandType.DIM, 9))
        self.assertEqual(DimmerCommand.parse(" 0 "), DimmerCommand(DimmerCommandType.OFF))
        self.assertEqual(DimmerCommand.parse(" 100 "), DimmerCommand(DimmerCommandType.DIM, 100))

        with self.assertRaises(ValueError):
            DimmerCommand.parse("onnnnn")
        with self.assertRaises(ValueError):
            DimmerCommand.parse("")
        with self.assertRaises(ValueError):
            DimmerCommand.parse("-2")
        with self.assertRaises(ValueError):
            DimmerCommand.parse(None)

    def test_str(self):
        self.assertEqual(str(DimmerCommand(DimmerCommandType.ON)), "ON")
        self.assertEqual(str(DimmerCommand(DimmerCommandType.OFF)), "OFF")
        self.assertEqual(str(DimmerCommand(DimmerCommandType.DIM, 9)), "9")
