# Release notes

## v4.0.0 (2021-xx-xx)

- lot of refactoring
  - configuration changes (now via JSON Schema)
  - inhertiance hierarchy flattend
- supports Eltako FSB61NB-230V (roller shutter relais)
- "rocker scenes"
  - run predefined commands via rocker switches (EEP F6-02-02) 
  - supported by Eltako FSB61NB-230V, Eltako FUD61 and ELtako FSR61
- removed Fud61SimpleSwitch (functionality replaced by "rocker scenes")
- removed separate teach mode (teaching is done via MQTT commond now)
- documentation updated
