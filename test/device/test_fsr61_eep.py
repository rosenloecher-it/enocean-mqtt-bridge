import unittest

from src.common.switch_state import SwitchState
from src.device.fsr61_eep import Fsr61Action, Fsr61Command, Fsr61Eep


class TestFsr61Eep(unittest.TestCase):

    def test_loop(self):
        actions = [
            Fsr61Action(
                command=Fsr61Command.STATUS_REQUEST,
            ),
            Fsr61Action(
                command=Fsr61Command.SWITCHING,
                switch_state=SwitchState.ON,
            ),
            Fsr61Action(
                command=Fsr61Command.SWITCHING,
                switch_state=SwitchState.OFF,
            ),
        ]

        for action_in in actions:
            if action_in.sender is None:
                action_in.sender = 1  # default

            packet = Fsr61Eep.create_packet(action_in)
            action_out = Fsr61Eep.extract_packet(packet, action_in.command)

            self.assertEqual(action_out.command, action_in.command)

            if action_in.command == Fsr61Command.SWITCHING:
                self.assertEqual(action_out.switch_state, action_in.switch_state)
