import copy
import unittest

from src.device.misc.rocker_switch_tools import RockerAction, RockerPress, RockerButton, RockerSwitchTools


class TestRockerPress(unittest.TestCase):

    def test_to_string(self):
        self.assertEqual(str(RockerPress.RELEASE), "RELEASE")
        self.assertEqual(repr(RockerPress.PRESS_SHORT), "PRESS_SHORT")

    def test_equal(self):
        for e1 in RockerPress:
            e2 = copy.deepcopy(e1)
            self.assertEqual(e1, e2)


class TestRockerButton(unittest.TestCase):

    def test_to_string(self):
        self.assertEqual(str(RockerButton.ROCK0), "ROCK0")
        self.assertEqual(repr(RockerButton.ROCK1), "ROCK1")

    def test_convert(self):
        for b in RockerButton:
            self.assertEqual(RockerButton.convert(b.value), b)

        self.assertEqual(RockerButton.convert("non_sense"), None)

    def test_equal(self):
        for b1 in RockerButton:
            b2 = copy.deepcopy(b1)
            self.assertEqual(b1, b2)

        self.assertNotEqual(RockerButton.ROCK0, RockerButton.ROCK1)
        self.assertNotEqual(RockerButton.ROCK0, "RockerButton.ROCK0")


class TestRockerAction(unittest.TestCase):

    @classmethod
    def get_actions(self):
        actions = [
            RockerAction(RockerPress.RELEASE, None)
        ]

        for p in [RockerPress.PRESS_LONG, RockerPress.PRESS_SHORT]:
            for b in RockerButton:
                actions.append(RockerAction(button=b, press=p))

        return actions

    def test_to_string(self):
        self.assertEqual(str(RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)),
                         "PRESS_SHORT-ROCK1")
        self.assertEqual(repr(RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK2)),
                         "RockerAction(PRESS_LONG-ROCK2)")

    def test_equal(self):
        actions = self.get_actions()

        for a1 in actions:
            a2 = copy.deepcopy(a1)
            self.assertEqual(a2, a1)


class TestRockerSwitch(unittest.TestCase):

    def test_1(self):
        actions = [
            RockerAction(RockerPress.RELEASE, None)
        ]

        # for p in [RockerPress.PRESS_LONG, RockerPress.PRESS_SHORT]:
        #     for b in RockerButton:
        #         actions.append(RockerAction(button=b, press=p))

        for action_in in actions:
            props_in = RockerSwitchTools.create_props(action_in)
            packet = RockerSwitchTools.create_packet(action_in)
            props_out = RockerSwitchTools.extract_props(packet)
            actions_out = RockerSwitchTools.extract_action(props_out)

            self.assertEqual(props_out, props_in)
            self.assertEqual(actions_out, action_in)

        # create_props -> {}
        # create_packet_from_props -> paket
        # extract_props -> {}
        # extract_button
