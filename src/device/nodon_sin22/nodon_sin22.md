# NodOn SIN-2-2-01

The NodOn SIN-2-2-01 is a 2-channel ON/OFF lighting relay switch.

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
