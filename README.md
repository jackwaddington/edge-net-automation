# edge-net-automation

A node in [edge-net](https://github.com/jackwaddington/edge-net). A Pi 3A with a Pimoroni Automation Hat, connected to the edge-net WiFi. Primary use case: graceful shutdown sequencing — SSH into a node, wait for it to halt, then cut power via relay.

## Hardware

- Raspberry Pi 3A
- Pimoroni Automation Hat

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

- Connected to the edge-net WiFi, SSH-accessible from other nodes
- Controls relays to switch power to devices (separate 24V supply required)
- Graceful shutdown sequence: SSH into target node → issue shutdown → wait for halt → open relay to cut power
- Subscribes to MQTT topics to receive shutdown or control commands

## Software

Python on Raspberry Pi OS. SSH-accessible over the edge-net WiFi, so code can be updated without physical access.

## MQTT topics

| Topic | Direction | Description |
| ----- | --------- | ----------- |
| TBD | subscribe | Shutdown or relay control commands |

## Part of edge-net

See [edge-net](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
