# enocean-mqtt-bridge

Bridges and translates Enocean messages between a (USB) gateway to a MQTT broker for specific devices. 
Runs as Linux service (e.g. on Raspberry Pi).

The MQTT messages can be further processed with other smarthome systems (e.g. Openhab, Home Assistant, Loxone).
These smarthome systems may support the listed devices directly.
But decoupling the systems and use a separated MQTT message broker has some advantages.
You can access the smarthome state via generic MQTT clients and don't have to use proprietary APIs.
(Useful, when you want to write your own rules independently of a dedicated smarthome system.)
In the end you could degrade your smarthome system to a pure GUI tool and switch easily between different ones.

## Features

- Configurable MQTT last will / testament (for example an "OFFLINE" status can be predefined at MQTT level for connection interrupts)
- Live cycle management (restarts) are supposed to be handled by systemd (script provided).
- Supported/tested Enocean gateways:
  - DOSMUNG Gateway USB Stick with SMA Port, chipset TCM 310
- Supported/tested Enocean devices:
  - [Eltako FFG7B-rw (nearly identical to Eltako TF-FGB; windows handle)](./docs/eltako_ffg7b.md)
  - [Eltako FSB61NB-230V (roller shutter)](./docs/eltako_fsb61.md)
  - [Eltako FSR61-230V (ON/OFF relay switch)](./docs/eltako_fsr61.md)
  - [Eltako FUD61NP(N)-230V (dimmer)](./docs/eltako_fud61.md)
  - [NodOn SIN-2-2-01 (2-channel ON/OFF lighting relay switch)](./docs/nodon_sin22.md)
  - [RockerSwitch (manual wireless radio switch; forwards manual click events as MQTT commands)](./docs/rocker_switch.md)
- Not supported:
  - Nodon SIN-2-RS-01: Not reliable to pair. Questions were not answered by Nodon.

## Release notes

[See here](./docs/release_notes.md)

## Requirements

- Python 3.7+
- Linux / Raspberry Pi

## Startup

### Get access to USB stick
```bash
# enable access to Enocean USB stick (alternative set user mode directly)
sudo usermod -a -G dialout $USER
# logout & login
```

### Test working MQTT broker (here Mosquitto)
```bash
sudo apt-get install mosquitto-clients

# preprare credentials
SERVER="<your server>"

# start listener
mosquitto_sub -h $SERVER -p 1883 -i "client_sub" -d -t smarthome/#

# send single message
mosquitto_pub -h $SERVER -p 1883 -i "client_pub" -d -t smarthome/test -m "test_$(date)"

# just as info: clear retained messages
mosquitto_pub -h $SERVER -p 1883 -i "client_pub" -d -t smarthome/test -n -r -d
```

### Prepare python environment
```bash
cd /opt
sudo mkdir enocean-mqtt-bridge
sudo chown pi:pi enocean-mqtt-bridge  # type in your user
git clone https://github.com/rosenloecher-it/enocean-mqtt-bridge enocean-mqtt-bridge

cd enocean-mqtt-bridge
virtualenv -p /usr/bin/python3 venv

# activate venv
source ./venv/bin/activate

# check python version >= 3.7
python --version

# install required packages
pip install -r requirements.txt
```

### Configuration

```bash
# cd ... goto project dir
cp ./enocean-mqtt-bridge.yaml.sample ./enocean-mqtt-bridge.yaml
```

Edit your `enocean-mqtt-bridge.yaml`. See comments there. 

**Enocean Base ID**

Your USB gateway has an internal Enocean ID (== **Base** ID). Enocean IDs are used to identify devices and link device to each other by a 
teaching in process. If you want to manage different devices by **one** USB gateway, then you have to use different Enocean **sender** IDs! 
Otherwise multiple actors will react on each command, which might not what you want. (If you don't configure an Enocean **sender** ID, 
the Gateway Enocean **Base** ID is used at teaching in.) 

For each control channel you have to define your own Enocean **sender** IDs. You can free choose the IDs, but have to stay within the range 
[Enocean **Base** ID + 1, Enocean **Base** ID + X]. The Enocean **Base** ID is different for every individual gateway. It gets logged out 
at service start in the log file or to the console. The possible count of individual sender IDs is supposed about 128. 

### Run

```bash
# see command line options
./enocean-mqtt-bridge.sh --help

# prepare your own config file based on ./enocean-mqtt-bridge.yaml.sample
./enocean-mqtt-bridge.sh -p -c ./enocean-mqtt-bridge.yaml
```

## Register as systemd service
```bash
# prepare your own service script based on enocean-mqtt-bridge.service.sample
cp ./enocean-mqtt-bridge.service.sample ./enocean-mqtt-bridge.service

# edit/adapt pathes and user in enocean-mqtt-bridge.service
vi ./enocean-mqtt-bridge.service

# install service
sudo cp ./enocean-mqtt-bridge.service /etc/systemd/system/
# alternativ: sudo cp ./enocean-mqtt-bridge.service.sample /etc/systemd/system//enocean-mqtt-bridge.service
# after changes
sudo systemctl daemon-reload

# start service
sudo systemctl start enocean-mqtt-bridge

# check logs
journalctl -u enocean-mqtt-bridge
journalctl -u enocean-mqtt-bridge --no-pager --since "5 minutes ago"

# enable autostart at boot time
sudo systemctl enable enocean-mqtt-bridge.service
```

## Troubleshooting

There happened some very quick connects/disconnects from/to MQTT broker (Mosquitto) on a Raspberry Pi. The connection
was secured only by certificate. The problem went away after configuring username and password for the MQTT broker.
On an Ubuntu system all was working fine even without user and password.

`sudo service enocean-mqtt-bridge status`

Mar 18 06:22:18 roofpi systemd[1]: enocean-mqtt-bridge.service: Current command vanished from the unit file, execution of the command list won't be resumed.

```bash
sudo systemctl disable enocean-mqtt-bridge.service
sudo rm /etc/systemd/system/enocean-mqtt-bridge.service
sudo systemctl daemon-reload

sudo cp ./enocean-mqtt-bridge.service /etc/systemd/system/
sudo rm /etc/systemd/system/enocean-mqtt-bridge.service
sudo service enocean-mqtt-bridge start
sudo systemctl enable enocean-mqtt-bridge.service
```

## Related projects

- Inspiration, but did not fully meet my needs: [https://github.com/embyt/enocean-mqtt](https://github.com/embyt/enocean-mqtt)
- Based on: [https://github.com/kipe/enocean](https://github.com/kipe/enocean)
- Node-RED documentation for Enocean profiles: [https://enocean-js.github.io/enocean-js/?eep=f6-02-02](https://enocean-js.github.io/enocean-js/?eep=f6-02-02)


## Maintainer & License

MIT © [Raul Rosenlöcher](https://github.com/rosenloecher-it)

The code is available at [GitHub][home].

[home]: https://github.com/rosenloecher-it/enocean-mqtt-bridge
