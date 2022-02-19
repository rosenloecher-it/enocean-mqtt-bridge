# RockerSwitch 

A "RockerSwitch" listen to that wireless radio switches. When a user clicks a button, a button number and action type (short/long) 
is sent to an MQTT channel.  

## Features

- Outputs JSON
    ```json
    {
      "status": "SHORT",
      "button": 3,
      "timestamp": "2021-10-21T10:49:42.010918+02:00"
    }
    ```
  
## Device configuration

```yaml
  switch-office:
    enocean_target:       0xfef2a47b
    device_type:          "RockerSwitch"

    # mqtt_channel_0, mqtt_channel_1: optional
    mqtt_channel_2:       "test/lights/office-switch"
    mqtt_channel_3:       "test/lights/office-switch"
    mqtt_channel_long_2:  "test/lights/office-switch"
    mqtt_channel_long_3:  "test/lights/office-switch"
```
