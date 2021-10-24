# Release notes

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
