"""Edge-NET demo rule: keybow buttons drive the Pi 3A relays, with LED feedback
that reflects the round-trip and the real relay state.

Choreography per button N (-> relay N+1):
  press   -> LED N goes YELLOW   (ack: the press made it across the bus)
  release -> toggle relay N      (the release is what actually switches it)
           -> LED N goes GREEN (relay now on) or RED (relay now off)

So the LED is a live probe of the whole loop: press/release edges, the MQTT
round-trip, and the actual relay state. This is the one piece that knows which
button maps to which relay — neither node does. It lives above the bus and
bridges keybow's bare-string dialect to the relay node's JSON.
"""

import json
import time

import paho.mqtt.client as mqtt

BROKER, PORT = "10.1.1.1", 1883

# button index (0..2)  ->  relay number (1..3)
BUTTON_RELAY = {0: 1, 1: 2, 2: 3}

TOPIC_BUTTON = "edge-net/keybow/button/{}"      # subscribe (bare "press"/"release")
TOPIC_LED    = "edge-net/keybow/led/{}"         # publish bare "r,g,b" (keybow's dialect)
TOPIC_RELAY  = "edge-net/automation/relay/{}"   # publish JSON {"state": ...}

YELLOW, GREEN, RED = "255,255,0", "0,255,0", "255,0,0"

# The rule holds relay state, because neither dumb node does.
relay_on = {1: False, 2: False, 3: False}

# Idempotency (D5): a button release can arrive twice — mechanical bounce, or a
# QoS-1 retransmit on a lossy link — and each would flip the relay. Collapse
# releases that land within this window into one toggle.
RELEASE_DEBOUNCE = 0.3
last_release = {1: 0.0, 2: 0.0, 3: 0.0}


def event_of(payload):
    """keybow publishes bare 'press'/'release'; also accept JSON {"event": ...}."""
    p = payload.decode().strip()
    if p in ("press", "release"):
        return p
    try:
        return json.loads(p).get("event")
    except ValueError:
        return None


def on_connect(client, userdata, flags, rc):
    print(f"Rule connected (rc={rc})")
    # Start from a known state: relays off, LEDs red. Retained, so keybow picks
    # the colours up the moment it (re)subscribes.
    for b, relay in BUTTON_RELAY.items():
        client.subscribe(TOPIC_BUTTON.format(b), qos=1)
        relay_on[relay] = False
        client.publish(TOPIC_RELAY.format(relay),
                       json.dumps({"state": "off"}), qos=1, retain=True)
        client.publish(TOPIC_LED.format(b), RED, qos=1, retain=True)


def on_message(client, userdata, msg):
    for b, relay in BUTTON_RELAY.items():
        if msg.topic != TOPIC_BUTTON.format(b):
            continue
        ev = event_of(msg.payload)
        if ev == "press":
            # Acknowledge the press round-trip: LED yellow (pending).
            client.publish(TOPIC_LED.format(b), YELLOW, qos=1, retain=True)
            print(f"button {b} press -> LED yellow")
        elif ev == "release":
            # Ignore a duplicate/bounced release within the debounce window.
            now = time.time()
            if now - last_release[relay] < RELEASE_DEBOUNCE:
                return
            last_release[relay] = now
            # Release is what actually switches the relay.
            relay_on[relay] = not relay_on[relay]
            state = "on" if relay_on[relay] else "off"
            client.publish(TOPIC_RELAY.format(relay),
                           json.dumps({"state": state}), qos=1, retain=True)
            client.publish(TOPIC_LED.format(b),
                           GREEN if relay_on[relay] else RED, qos=1, retain=True)
            print(f"button {b} release -> relay {relay} {state} -> LED "
                  f"{'green' if relay_on[relay] else 'red'}")
        return


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_forever()
