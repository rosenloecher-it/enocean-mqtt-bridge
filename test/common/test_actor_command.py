import unittest

from src.common.actor_command import ActorCommand


class TestActorCommand(unittest.TestCase):

    def test_parse_switch(self):
        self.assertEqual(ActorCommand.parse_switch(" On "), ActorCommand.ON)
        self.assertEqual(ActorCommand.parse_switch(" 1 "), ActorCommand.ON)
        self.assertEqual(ActorCommand.parse_switch('{"state": " on "}'), ActorCommand.ON)
        self.assertEqual(ActorCommand.parse_switch(" oFF "), ActorCommand.OFF)
        self.assertEqual(ActorCommand.parse_switch(" 0 "), ActorCommand.OFF)
        self.assertEqual(ActorCommand.parse_switch('{"STATE": " ofF "}'), ActorCommand.OFF)
        self.assertEqual(ActorCommand.parse_switch('{"command": " ofF "}'), ActorCommand.OFF)
        self.assertEqual(ActorCommand.parse_switch('{"cmd": " ofF "}'), ActorCommand.OFF)

        self.assertEqual(ActorCommand.parse_switch(" learn "), ActorCommand.LEARN)
        self.assertEqual(ActorCommand.parse_switch(" teach "), ActorCommand.LEARN)
        self.assertEqual(ActorCommand.parse_switch(" teach-IN "), ActorCommand.LEARN)
        self.assertEqual(ActorCommand.parse_switch(" Update "), ActorCommand.UPDATE)
        self.assertEqual(ActorCommand.parse_switch(" refresh "), ActorCommand.UPDATE)

        with self.assertRaises(ValueError):
            ActorCommand.parse_switch("onnnnn")
        with self.assertRaises(ValueError):
            ActorCommand.parse_switch("77")
        with self.assertRaises(ValueError):
            ActorCommand.parse_switch("")
        with self.assertRaises(ValueError):
            ActorCommand.parse_switch(None)

    def test_parse_dimmer(self):

        self.assertEqual(ActorCommand.parse_dimmer(" On "), (ActorCommand.ON, None))
        self.assertEqual(ActorCommand.parse_dimmer('{"STATE": " on "}'), (ActorCommand.ON, None))
        self.assertEqual(ActorCommand.parse_dimmer(" oFF "), (ActorCommand.OFF, None))
        self.assertEqual(ActorCommand.parse_dimmer('{"STATE": " ofF "}'), (ActorCommand.OFF, None))
        self.assertEqual(ActorCommand.parse_dimmer(" learn "), (ActorCommand.LEARN, None))
        self.assertEqual(ActorCommand.parse_dimmer(" teach "), (ActorCommand.LEARN, None))
        self.assertEqual(ActorCommand.parse_dimmer(" teach-IN "), (ActorCommand.LEARN, None))
        self.assertEqual(ActorCommand.parse_dimmer(" Update "), (ActorCommand.UPDATE, None))
        self.assertEqual(ActorCommand.parse_dimmer(" refresh "), (ActorCommand.UPDATE, None))

        self.assertEqual(ActorCommand.parse_dimmer(" 1 "), (ActorCommand.DIM, 1))
        self.assertEqual(ActorCommand.parse_dimmer(" 77 "), (ActorCommand.DIM, 77))
        self.assertEqual(ActorCommand.parse_dimmer('{"STATE": " 9 "}'), (ActorCommand.DIM, 9))
        self.assertEqual(ActorCommand.parse_dimmer(" 0 "), (ActorCommand.OFF, None))
        self.assertEqual(ActorCommand.parse_dimmer(" 100 "), (ActorCommand.DIM, 100))

        with self.assertRaises(ValueError):
            ActorCommand.parse_dimmer("onnnnn")
        with self.assertRaises(ValueError):
            ActorCommand.parse_dimmer("")
        with self.assertRaises(ValueError):
            ActorCommand.parse_dimmer("-2")
        with self.assertRaises(ValueError):
            ActorCommand.parse_dimmer(None)

    def test_print(self):
        self.assertEqual(str(ActorCommand.ON), "ON")
        self.assertEqual(repr(ActorCommand.OFF), "ActorCommand(OFF)")
        self.assertEqual(str((ActorCommand.DIM, 9)), "(ActorCommand(DIM), 9)")  # tuple format == repr
