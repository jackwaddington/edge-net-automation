"""Edge-NET rule: button presses from ANY input node drive the Pi 3A relays.

Generalised from the keybow-only demo. Any (node, button) in SOURCES toggles its
mapped relay on release. The keybow additionally gets LED feedback (press=yellow,
release=green/red) because it has LEDs; other sources (gamepad, gfx, inky) just
toggle the relay. Many controls can share one relay — press the "first button" on
*any* node and relay 1 flips. This rule is the one piece that knows which button
maps to which relay; the dumb nodes don't. It lives above the bus.

Choreography per mapped button (-> relay R):
  press   -> (keybow only) LED yellow   (ack: the press crossed the bus)
  release -> toggle relay R             (the release is what switches it)
           -> (keybow only) LED green (on) / red (off), as a live relay probe
"""

import json
import time

import paho.mqtt.client as mqtt

BROKER, PORT = "10.1.1.1", 1883

# (node, button) -> relay number (1..3). Many controls may share a relay.
SOURCES = {
    ("keybow", "0"): 1, ("keybow", "1"): 2, ("keybow", "2"): 3,
    ("gamepad", "a"): 1, ("gamepad", "b"): 2, ("gamepad", "x"): 3,
    ("gfx", "a"): 1, ("gfx", "b"): 2, ("gfx", "c"): 3,
    ("inky", "a"): 1, ("inky", "b"): 2, ("inky", "c"): 3,
}

TOPIC_BUTTON     = "edge-net/{}/button/{}"        # .format(node, button)
TOPIC_RELAY      = "edge-net/automation/relay/{}" # publish JSON {"state": ...}
TOPIC_KEYBOW_LED = "edge-net/keybow/led/{}"       # only the keybow has LEDs
TOPIC_STRIP      = "edge-net/gamepad/led"         # the Plasma stick's 50-LED strip
TOPIC_INKY       = "edge-net/inky/display"        # Inky display: {"text": "...", "face": "..."}

# What the Inky shows when its own buttons are pressed. All logic here, none on device.
INKY_PHRASES = {
    "a": ("Aamu on barbaari!", ">:("),
    "b": ("Aiti on tuhma!",   ":P"),
    "c": ("Jack on komea!",   ":)"),
}

YELLOW, GREEN, RED = "255,255,0", "0,255,0", "255,0,0"

# Solid colour the strip flashes while a button is held, per relay; idle between.
STRIP_COLOUR = {1: "255,0,0", 2: "0,255,0", 3: "0,0,255"}
STRIP_IDLE = "0,40,80"          # calm teal when nothing is pressed

# The rule holds relay state, because neither dumb node does.
relay_on = {1: False, 2: False, 3: False}

# Idempotency (D5): a release can arrive twice (bounce, or a QoS-1 retransmit on a
# lossy link). Collapse releases that land within this window into one toggle.
RELEASE_DEBOUNCE = 0.3
last_release = {1: 0.0, 2: 0.0, 3: 0.0}

# relay -> [keybow button ids on it], so the keybow LED stays a true relay probe
# even when a *different* node toggled the relay.
KEYBOW_FOR_RELAY = {}
for (_node, _button), _relay in SOURCES.items():
    if _node == "keybow":
        KEYBOW_FOR_RELAY.setdefault(_relay, []).append(_button)


def parse_button_topic(topic):
    """edge-net/<node>/button/<button>  ->  (node, button)  or (None, None)."""
    parts = topic.split("/")
    if len(parts) == 4 and parts[0] == "edge-net" and parts[2] == "button":
        return parts[1], parts[3]
    return None, None


def event_of(payload):
    """Nodes publish bare 'press'/'release'; also accept JSON {"event": ...}."""
    p = payload.decode().strip()
    if p in ("press", "release"):
        return p
    try:
        return json.loads(p).get("event")
    except ValueError:
        return None


def refresh_keybow(client, relay):
    colour = GREEN if relay_on[relay] else RED
    for button in KEYBOW_FOR_RELAY.get(relay, []):
        client.publish(TOPIC_KEYBOW_LED.format(button), colour, qos=1, retain=True)


def inky_show(client, text, face=None):
    payload = {"text": text}
    if face:
        payload["face"] = face
    client.publish(TOPIC_INKY, json.dumps(payload), qos=1)


def set_relay(client, relay, on):
    relay_on[relay] = on
    client.publish(TOPIC_RELAY.format(relay),
                   json.dumps({"state": "on" if on else "off"}),
                   qos=1, retain=True)
    inky_show(client, f"Relay {relay} {'on' if on else 'off'}")


def on_connect(client, userdata, flags, rc):
    print(f"Rule connected (rc={rc})")
    for (node, button) in SOURCES:
        client.subscribe(TOPIC_BUTTON.format(node, button), qos=1)
    for relay in (1, 2, 3):
        set_relay(client, relay, False)
        refresh_keybow(client, relay)
    client.publish(TOPIC_STRIP, STRIP_IDLE)


def on_message(client, userdata, msg):
    node, button = parse_button_topic(msg.topic)
    ev = event_of(msg.payload)

    # Inky buttons show Finnish phrases — don't toggle relays
    if node == "inky" and button in INKY_PHRASES and ev == "press":
        text, face = INKY_PHRASES[button]
        inky_show(client, text, face)
        print(f"inky {button} press -> phrase: {text}")
        return

    relay = SOURCES.get((node, button))
    if relay is None:
        return
    if ev == "press":
        if node == "keybow":
            client.publish(TOPIC_KEYBOW_LED.format(button), YELLOW, qos=1, retain=True)
        client.publish(TOPIC_STRIP, STRIP_COLOUR[relay])
        print(f"{node} {button} press -> relay {relay} (pending)")
    elif ev == "release":
        now = time.time()
        if now - last_release[relay] < RELEASE_DEBOUNCE:
            return
        last_release[relay] = now
        set_relay(client, relay, not relay_on[relay])
        refresh_keybow(client, relay)
        client.publish(TOPIC_STRIP, STRIP_IDLE)
        print(f"{node} {button} release -> relay {relay} "
              f"{'on' if relay_on[relay] else 'off'}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_forever()
