# edge-net-automation

A node in [Edge-NET](https://github.com/jackwaddington/edge-net). A Pi 3A with a Pimoroni Automation Hat, connected to the edge-net WiFi. Primary use case: graceful shutdown sequencing — SSH into a node, wait for it to halt, then cut power via relay.

## Hardware

- [Raspberry Pi 3A](https://www.raspberrypi.com/products/raspberry-pi-3-model-a-plus/)
- [Pimoroni Automation Hat](https://shop.pimoroni.com/products/automation-hat)

### Automation Hat I/O

| Feature | Spec |
| ------- | ---- |
| Relays | 3 × 24V @ 2A (NC and NO terminals) |
| ADC inputs | 3 × 12-bit @ 0–24V (±2% accuracy) |
| Buffered inputs | 3 × 24V tolerant |
| Sinking outputs | 3 × 24V tolerant |
| Low-voltage ADC | 1 × 12-bit @ 0–3.3V |
| Connectors | 3.5mm screw terminals |
| Indicators | 15 × channel LEDs, Power / Comms / Warn LEDs |
| Broken out pins | SPI, TX (#14), RX (#15), #25 |

## What it does

- Connected to the Edge-NET WiFi, SSH-accessible from other nodes
- Controls relays to switch power to devices (separate 24V supply required)
- Graceful shutdown sequence: SSH into target node → issue shutdown → wait for halt → open relay to cut power
- Subscribes to MQTT topics to receive shutdown or control commands

## Software

Python on Raspberry Pi OS. SSH-accessible over the edge-net WiFi, so code can be updated without physical access.

## MQTT topics

### Relay (relay_node.py / rule.py)

| Topic | Direction | Description |
| ----- | --------- | ----------- |
| `edge-net/automation/relay/{1,2,3}` | subscribe | `{"state":"on"}` / `{"state":"off"}` |
| `edge-net/automation/status` | publish | LWT liveness |

### Audio (audio_service.py)

| Topic | Direction | Payload |
| ----- | --------- | ------- |
| `edge/hub/audio/play` | subscribe | `{"file":"chime.wav"}` / `{"tts":"some text"}` / `{"volume":70}` |
| `edge/hub/audio/state` | publish | `{"status":"playing","source":"…"}` / `{"status":"idle"}` |

## Audio service install

```bash
# On the Pi 3A
pip install paho-mqtt
sudo apt install espeak          # TTS fallback (always available)
sudo apt install piper           # preferred TTS — skip if unavailable

# Copy sounds to expected location
sudo mkdir -p /opt/edge-net/sounds
sudo cp sounds/chime.wav /opt/edge-net/sounds/

# Deploy systemd unit
sudo cp systemd/edge-net-audio.service /etc/systemd/system/
sudo systemctl enable --now edge-net-audio

# Test
mosquitto_pub -h 10.1.1.1 -t edge/hub/audio/play -m '{"tts":"hello world"}'
mosquitto_pub -h 10.1.1.1 -t edge/hub/audio/play -m '{"file":"chime.wav"}'
```

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
