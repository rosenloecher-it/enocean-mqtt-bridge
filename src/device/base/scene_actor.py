from typing import Optional

import attr
from paho.mqtt.client import MQTTMessage

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.device.base.device import Device
from src.common.device_exception import DeviceException
from src.device.rocker_switch.rocker_switch_tools import RockerSwitchTools
from src.tools.enocean_tools import EnoceanTools

CONFKEY_ROCKER_SCENES = "rocker_scenes"


ROCKER_SCENE_JSONSCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "rocker_key": {"type": "integer", "enum": [0, 1, 2, 3], "description": "Rocker swicth button key."},
            "rocker_id": {"type": "integer", "description": "Enocean ID of the rocker switch."},
            "command": {"type": "string", "minLength": 1, "description": "Command like it it understood by MQTT."},
        },
        "additionalProperties": False,
        "required": ["rocker_key", "rocker_id", "command"],
    },
}


SCENE_ACTOR_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_ROCKER_SCENES: ROCKER_SCENE_JSONSCHEMA,
    },
}


@attr.s
class RockerScene:
    """Scenes are triggered by a rocker switches (EEP f6-02-02)"""
    rocker_key = attr.ib()  # type: int
    rocker_id = attr.ib()  # type: int
    command = attr.ib()  # type: str


class SceneActor(Device):

    def __init__(self, name: str):
        super().__init__(name)

        self._scenes = []  # type: list[RockerScene]

    def _set_config(self, config, skip_require_fields: [str]):
        super()._set_config(config, skip_require_fields)

        self.validate_config(config, SCENE_ACTOR_JSONSCHEMA)

        rocker_scenes = config.get(CONFKEY_ROCKER_SCENES, [])
        for scene in rocker_scenes:
            self._scenes.append(RockerScene(**scene))

    @property
    def enocean_targets(self):
        return list({self._enocean_target, *[s.rocker_id for s in self._scenes]})

    def find_rocker_scene(self, packet: RadioPacket) -> Optional[RockerScene]:
        if packet.packet_type == PACKET.RADIO and packet.rorg == RockerSwitchTools.DEFAULT_EEP.rorg:
            scenes = [s for s in self._scenes if s.rocker_id == packet.sender_int]
            if scenes:
                try:
                    rocker_action = RockerSwitchTools.extract_action_from_packet(packet)
                    scenes = [s for s in scenes if s.rocker_key == rocker_action.button]
                except DeviceException:
                    scenes = None
                    EnoceanTools.log_pickled_enocean_packet(self._logger.warning, packet, "find_rocker_scene - cannot extract")

                if scenes:
                    return scenes[0]

        return None

    def process_rocker_scene(self, scene: RockerScene):
        if scene:
            message = MQTTMessage()
            message.payload = scene.command if isinstance(scene.command, bytes) else scene.command.encode()
            self._logger.debug("process rocker scene: %s", scene)
            self.process_mqtt_message(message)
