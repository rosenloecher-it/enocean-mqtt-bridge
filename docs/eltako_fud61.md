
# Eltako FUD61NP(N)-230V

Eltako FUD61NP(N)-230V is a dimmer.

## Features

- Dim and switch ON/OFF and get notifications about state changes. Delivers dim state in %.
- Cyclic update requests to detect missed state changes or an  offline device.
- Outouts JSON
    ```json
    {
      "timestamp": "2021-10-21T10:25:37.438799+02:00", 
      "state": "on", 
      "dim_state": 77, 
      "rssi": -60
    }
    ```
- Activates predefined "rocker scenes". The bridge listen to separate rocker switches and execute 
  the predefiend commands. The switches do not have to be teached in.

## MQTT Commands

- on, off, toggle
- 0 to 100 for dimming
- update: requests an update from the device and sends the current postion via MQTT.
- learn: Teach the device. Bring the device in teach mode and then send "learn".

All commands are case in-sensitive.

## Device configuration

```yaml
devices:
  
  child-dimmer:
    device_type:            "EltakoFud61"
    enocean_sender:         0x22222222      # your Enocean sender ID (specific to you USB device!)
    enocean_target:         0x01231233      # Enocean ID of the relay switch
    mqtt_channel_cmd:       "test/child-dimmer/cmd"
    mqtt_channel_state:     "test/child-dimmer/state"
    mqtt_retain:            True
    mqtt_time_offline:      900
    rocker_scenes:          [
                                {"rocker_id": 0x44444444, "rocker_key": 2, "command": "toggle"},
                                {"rocker_id": 0x44444444, "rocker_key": 3, "command": "toggle"},
                            ]
```
