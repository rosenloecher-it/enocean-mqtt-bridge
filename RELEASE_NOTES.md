# Release notes

## v5.2 (2023-03-25)

- requirement upgrades
- fix not implemented LEARN command for Nodon Sin22

## v5.1 (2022-12-29)

- refactoring: changed device structure
- "OpeningSensor" (renamed from "EltakoFFG7B") supports now:
  - Eltako FTKB (magnetic contact, EEP telegram D5-00-01)
  - Nodon SDO-2-1-05 (magnetic contact, EEP telegram D5-00-01)
  - no change: Eltako FFG7B
- Bootstraping MQTT client changed. Fixed: "MqttConnector not set!"


## v5.0 (2022-07-07)

- JSON messages changed: all JSON attributes are now camel-case 


## v4.0 (2022-02-19)

- JSON messages changed: renamed attribute "state" to "status"


## v3.1 (2021-10-24)

- lot of refactoring
  - configuration changes (now via JSON Schema)
  - inhertiance hierarchy flattend
- supports Eltako FSB61NB-230V (roller shutter relais)
- "rocker scenes"
  - run predefined commands via separate rocker switches (EEP F6-02-02; no need for teaching)
  - supported by Eltako FSB61NB-230V, Eltako FUD61 and ELtako FSR61
- removed Fud61SimpleSwitch (functionality replaced by "rocker scenes")
- removed separate teach mode (teaching is done via MQTT commond now)
- MQTT (JSON) messages contain the device name for reference.
- documentation updated


## v3.0 (2021-09-19)

- refactoring
- device type keys (configuration) changed.
