
# Eltako FSB61NB-230V

The Eltako FSB61NB-230V is a roller shutter relais.

## Features

- Calulates postions based on driving times. 
- Seeks to concrete position. When no position is known, the shutter calibates itself  
  via long drives to the upper or lower end.
- 90% is es special position: The lower shutter edge is hiding the window/door, but the it is not really shut down,
  so that there are still gaps between the blades.
  - 0% - 90%: This range is called "driving". See configuration.
  - 90% - 100%: This range is called "rolling". See configuration.
- Activates predefined "rocker scenes". The bridge listen to separate rocker switches and execute 
  the predefiend commands. The switches do not have to be teached in.

## MQTT commands

- update: requests an update from the device and sends the current postion via MQTT.
- learn: Teach the device. Bring the device in teach mode and then send "learn".
- down
- up
- 0 - 100: seek to position
  - The position command may have a postfix "c" or "calibrate". That means a calibration is force and the shutter 
    drives via boundaries. "50 calibrate" (or "50c") would let the shutter go up with the longest time, wait for 
    arriving and seeking to the wished position. 

All commands are case in-sensitive.

## Device configuration

```yaml
devices:
  
  eltako-shutter:
    device_type:            "EltakoFsb61"
    enocean_sender:         0x22222222      # your Enocean sender ID (specific to you USB device!)
    enocean_target:         0x01231233      # Enocean ID of the relay switch
    mqtt_channel_cmd:       "test/eltako-shutter/cmd"
    mqtt_channel_state:     "test/eltako-shutter/state"
    mqtt_retain:            False
    mqtt_time_offline:      300
    storage_file:           "./__work__/eltako-shutter.yaml"

    # times to measure for each individual shutter!
    time_up_rolling:        6
    time_up_driving:        10.1
    time_down_rolling:      4
    time_down_driving:      9

    rocker_scenes:          [
                                {"rocker_id": 0x44444444, "rocker_key": 2, "command": "90 calibrate"},
                                {"rocker_id": 0x44444444, "rocker_key": 3, "command": "55 calibrate"},
                            ]
```
