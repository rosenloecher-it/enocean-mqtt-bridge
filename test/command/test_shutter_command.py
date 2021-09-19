import unittest

from src.command.shutter_command import ShutterCommand, ShutterCommandType


class TestShutterCommand(unittest.TestCase):

    def test_parse(self):

        self.assertEqual(ShutterCommand.parse(" Up   "), ShutterCommand(ShutterCommandType.POSITION, 0))
        self.assertEqual(ShutterCommand.parse("  DoWn"), ShutterCommand(ShutterCommandType.POSITION, 100))
        self.assertEqual(ShutterCommand.parse(" Off  "), ShutterCommand(ShutterCommandType.POSITION, 0))
        self.assertEqual(ShutterCommand.parse(" On   "), ShutterCommand(ShutterCommandType.POSITION, 100))

        self.assertEqual(ShutterCommand.parse(" 42   "), ShutterCommand(ShutterCommandType.POSITION, 42))
        self.assertEqual(ShutterCommand.parse(" 42.24"), ShutterCommand(ShutterCommandType.POSITION, 42))

        self.assertEqual(ShutterCommand.parse(" -10  "), ShutterCommand(ShutterCommandType.POSITION, 0))
        self.assertEqual(ShutterCommand.parse(" 120  "), ShutterCommand(ShutterCommandType.POSITION, 100))

        self.assertEqual(ShutterCommand.parse('{"STATE": " uP "}'), ShutterCommand(ShutterCommandType.POSITION, 0))
        self.assertEqual(ShutterCommand.parse('{"command": " DowN "}'),
                         ShutterCommand(ShutterCommandType.POSITION, 100))
        self.assertEqual(ShutterCommand.parse('{"cmd": " 50.5 "}'), ShutterCommand(ShutterCommandType.POSITION, 50))

        self.assertEqual(ShutterCommand.parse(" learn "), ShutterCommand(ShutterCommandType.LEARN))
        self.assertEqual(ShutterCommand.parse(" teach "), ShutterCommand(ShutterCommandType.LEARN))
        self.assertEqual(ShutterCommand.parse(" Update "), ShutterCommand(ShutterCommandType.UPDATE))
        self.assertEqual(ShutterCommand.parse(" refresh "), ShutterCommand(ShutterCommandType.UPDATE))

        self.assertEqual(ShutterCommand.parse(" stop "), ShutterCommand(ShutterCommandType.STOP))
