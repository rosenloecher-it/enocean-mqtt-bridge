
# Eltako FSR61-230V

The Eltako FSR61-230V is an ON/OFF relay switch. 

## Features

- Switch and get notifications about state changes.
- Cyclic update requests to detect missed state changes or an offline device.
- Outputs JSON:
    ```json
    {
      "timestamp": "2021-10-21T10:30:51.409471+02:00", 
      "state": "on", 
      "rssi": -49
    }
    ```

## MQTT Commands

- on, off, 0, 100, toggle
- update: requests an update from the device and sends the current postion via MQTT.
- learn: Teach the device. Bring the device in teach mode and then send "learn". 

All commands are case in-sensitive.

## Device configuration

```yaml
devicrs:
  
  office-light:
    device_type:          "EltakoFsr61"
    enocean_sender:       0x22222222      # your Enocean sender ID (specific to you USB device!)
    enocean_target:       0x01231233      # Enocean ID of the relay switch
    mqtt_channel_cmd:     "test/office-light/cmd"
    mqtt_channel_state:   "test/office-light/state"
    mqtt_retain:          True
    mqtt_time_offline:    900
```
