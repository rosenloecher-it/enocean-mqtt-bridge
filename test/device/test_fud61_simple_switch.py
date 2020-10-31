import unittest
from collections import namedtuple

from src.device.conf_device_key import ConfDeviceKey
from src.device.fud61_simple_switch import Fud61SimpleSwitch, Fud61SwitchAction
from src.enocean_connector import EnoceanMessage
from src.tools.rocker_switch_tools import RockerSwitchTools, RockerPress, RockerButton, RockerAction
from test.setup_test import SetupTest


class MockFud61SimpleSwitch(Fud61SimpleSwitch):

    def __init__(self, name):
        super().__init__(name)

        self.send_packets = []

    def _send_enocean_packet(self, packet, delay=0):
        self.send_packets.append(packet)

    def check_send_packes(self, result_state: bool) -> bool:
        if result_state is None:
            if len(self.send_packets) == 0:
                return True
            else:
                return False
        # else

        if len(self.send_packets) != 2:
            return False

        action = RockerSwitchTools.extract_action_from_packet(self.send_packets[0])
        expected_button_index = (1 if result_state else 0)  # default teach mode (this project)!
        if action.button.value != expected_button_index:
            return False

        return True


class TestFud61SimpleSwitch(unittest.TestCase):

    DIMMER_ID = 1001
    SWITCH_ID = 1002

    def setUp(self):
        SetupTest.set_dummy_sender_id()

    @classmethod
    def create_instance(cls, target_state: bool, additional_config=None) -> MockFud61SimpleSwitch:
        instance = MockFud61SimpleSwitch("switch")

        config = {
            ConfDeviceKey.ENOCEAN_TARGET.value: cls.DIMMER_ID,
            ConfDeviceKey.ENOCEAN_TARGET_SWITCH.value: cls.SWITCH_ID,
        }
        if additional_config:
            config.update(additional_config)
        instance.set_config(config)
        instance._target_state = target_state

        return instance

    def test_scenarios_auto(self):
        Scenario = namedtuple("Scenario", ["target_state", "action", "result"])

        scenarios = [
            # default ON
            Scenario(False, RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0), True),
            Scenario(False, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0), True),
            # default OFF
            Scenario(True, RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0), False),
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0), False),
            # not configured
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK2), None),
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK3), None),
            Scenario(True, RockerAction(RockerPress.RELEASE), None),
        ]

        for scenario in scenarios:
            instance = self.create_instance(scenario.target_state, {
                ConfDeviceKey.ROCKER_BUTTON_0.value: Fud61SwitchAction.AUTO.name,
                ConfDeviceKey.ROCKER_BUTTON_1.value: Fud61SwitchAction.AUTO.name,
            })

            packet = RockerSwitchTools.create_packet(scenario.action)
            message = EnoceanMessage(payload=packet, enocean_id=self.SWITCH_ID)
            instance.process_enocean_message(message)

            check = instance.check_send_packes(scenario.result)
            self.assertTrue(check)

    def test_scenarios_on_off(self):
        Scenario = namedtuple("Scenario", ["target_state", "action", "result"])

        scenarios = [
            # default ON
            Scenario(False, RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0), True),
            Scenario(False, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0), True),
            Scenario(True, RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK0), True),
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0), True),
            # default OFF
            Scenario(False, RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK1), False),
            Scenario(False, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1), False),
            Scenario(True, RockerAction(RockerPress.PRESS_LONG, RockerButton.ROCK1), False),
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1), False),
            # not configured
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK2), None),
            Scenario(True, RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK3), None),
            Scenario(True, RockerAction(RockerPress.RELEASE), None),
        ]

        for scenario in scenarios:
            instance = self.create_instance(scenario.target_state, {
                ConfDeviceKey.ROCKER_BUTTON_0.value: Fud61SwitchAction.ON.name,
                ConfDeviceKey.ROCKER_BUTTON_1.value: Fud61SwitchAction.OFF.name,
            })

            packet = RockerSwitchTools.create_packet(scenario.action)
            message = EnoceanMessage(payload=packet, enocean_id=self.SWITCH_ID)
            instance.process_enocean_message(message)

            check = instance.check_send_packes(scenario.result)
            self.assertTrue(check)
