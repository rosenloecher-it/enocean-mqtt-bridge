
# Opening sensor

Supports serveral devices:  
- Eltako FFG7B (nearly identical to Eltako TF-FGB; windows handle)
  - Supported is only the EEP telegram F6-10-00 (cyclic) which has to be configured at the device!
- Eltako FTKB (magnetic contact, EEP telegram D5-00-01)
- Nodon SDO-2-1-05 (magnetic contact, EEP telegram D5-00-01)

## Features

- Forwards state changes. Available states (`status`): 
  - `open`
  - `closed`
  - `tilted` (supported only by Eltako FFG7B)
  - `error` (when the received EEP telegram cannot be extracted)
  - or any status which is configured within the "last will" message 
- Check sensor state based on received messages and send a configurable "offline"/"last will" message if the device is silent  
  for a configurable timeout (`mqtt_time_offline`).
- Outputs JSON with time of last state change (`since`)
- JSON sample
  ```json
  {
      "status": "closed",
      "rssi": -61,
      "timestamp": "2020-03-16t21:09:37.205911+01:00",
      "since": "2020-03-15t19:09:37.205911+01:00"
  }
  ```


## Device configuration

```yaml
devices:

  windows-handle-sample:
    device_type:            "OpeningSensor"  # or for backwards compatibility "EltakoFFG7B"
    enocean_target:         0x01212212     
    mqtt_channel_state:     "test/windows-handle-sample"
    mqtt_qos:               2
    mqtt_retain:            True
    # Time (seconds) after which the device gets announced as offline if status message came in.    
    mqtt_time_offline:      3600    
    storage_file:           ./__work__/windows-handle-sample.yaml
```
