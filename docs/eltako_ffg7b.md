
# Eltako FFG7B-rw 

Eltako FFG7B-rw is a window handle. It's nearly identical to Eltako TF-FGB.

## Features

- check sensor state based on repeated messages and send a configurable OFFLINE message if the device is silent for a configurable timeout.
- Configuration device name: `EltakoFFG7B`
- outputs JSON with time of last state change (SINCE)
  ```json
  {
      "status": "closed",
      "rssi": -61,
      "timestamp": "2020-03-16t21:09:37.205911+01:00",
      "since": "2020-03-15t19:09:37.205911+01:00"
  }
  ```
- Transform states to (STATUS): OPEN, CLOSED, TILTED, OFFLINE, ERROR  
  

## Device configuration

```yaml
devices:

  windows-handle-sample:
    device_type:            "EltakoFFG7B"
    enocean_target:         0x01212212     
    mqtt_channel_state:   "test/windows-handle-sample"
    mqtt_qos:               2
    mqtt_retain:            True
    # Time (seconds) after which the device gets announced as offline if status message came in.    
    mqtt_time_offline:      3600    
    storage_file:         ./__work__/windows-handle-sample.yaml
```
