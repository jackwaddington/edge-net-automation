"""Edge-NET automation node: drive the Automation Hat relays from MQTT.

Subscribes to edge-net/automation/relay/{1,2,3}. Payload is JSON
{"state": "on"|"off"} (contract D2). Liveness via LWT on
edge-net/automation/status (contract D3). The node is dumb: it switches a
relay when told, nothing more — it does not decide *when*.
"""

import json
import socket

import paho.mqtt.client as mqtt
import automationhat

import config

# Map relay number (1..3) to the Automation Hat relay object.
_RELAY = {
    1: automationhat.relay.one,
    2: automationhat.relay.two,
    3: automationhat.relay.three,
}


def _ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((config.BROKER, config.PORT))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "?"


def on_connect(client, userdata, flags, rc):
    print(f"Connected to broker (rc={rc})")
    # Online state, retained (D3).
    client.publish(
        config.TOPIC_STATUS,
        json.dumps({"status": "online", "ip": _ip(), "fw": "relay-1"}),
        qos=1,
        retain=True,
    )
    for n in config.RELAYS:
        topic = config.TOPIC_RELAY.format(n)
        client.subscribe(topic, qos=1)
        print(f"Subscribed to {topic}")


def on_message(client, userdata, msg):
    # Find which relay this topic addresses.
    for n in config.RELAYS:
        if msg.topic == config.TOPIC_RELAY.format(n):
            try:
                state = json.loads(msg.payload.decode())["state"]
            except (ValueError, KeyError):
                print(f"Bad relay payload on {msg.topic}: {msg.payload!r}")
                return
            if state == "on":
                _RELAY[n].on()
            elif state == "off":
                _RELAY[n].off()
            else:
                print(f"Unknown state {state!r} on {msg.topic}")
                return
            print(f"Relay {n} -> {state}")
            return


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# LWT: the broker publishes this if we drop (D3). Frozen at connect, so minimal.
client.will_set(
    config.TOPIC_STATUS,
    json.dumps({"status": "offline"}),
    qos=1,
    retain=True,
)

client.connect(config.BROKER, config.PORT)
client.loop_forever()
