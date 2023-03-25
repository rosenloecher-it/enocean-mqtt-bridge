# NodOn SIN-2-2-01

The NodOn SIN-2-2-01 is a 2-channel ON/OFF lighting relay switch.

As the EEP profile D2-01-12 was not available in the enocean lib (former days),
the device is switched via standard rocker switch commands (EEP F6-02-02).
State changes are read automatically via EEP D2-01-01. 
Maybe these notifications have to be switched on. 

Unfortunatly the device got broken, so changes cannot be tested and there is not support possible any more. 

## Features
- Switch and get notifications about state changes.
- Output JSON

## MQTT commands

- on, off, 0, 100, toggle, update
- learn: Teach the device. Bring the device in teach mode and then send "learn".
- All commands are case in-sensitive.

## Device configuration

Configure a separate device for each channel!

```yaml
devices:
  
  channel1:
    enocean_target:       0x01111111        # Enocean ID of the relay switch
    enocean_sender:       0x22222228        # your Enocean sender ID (specific to you USB device!)
    device_type:          "NodonSin22"
    actor_channel:        0
    mqtt_channel_state:   "test/channel1/state"
    mqtt_retain:          True
    mqtt_channel_cmd:     "test/channel1/cmd"

  channel2:
    enocean_target:       0x01111111        # Enocean ID of the relay switch
    enocean_sender:       0x22222229        # your Enocean sender ID (specific to you USB device!)
    device_type:          "NodonSin22"
    actor_channel:        1
    mqtt_channel_state:   "test/channel2/state"
    mqtt_retain:          True
    mqtt_channel_cmd:     "test/channel2/cmd"
```
