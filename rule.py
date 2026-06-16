"""Edge-NET demo rule: keybow buttons toggle the Pi 3A relays.

This is the one piece that knows "button N controls relay N+1". Neither node
knows about the other — pull this rule and they are strangers again. It lives
*above* the bus (orchestration), not inside either node. Run it anywhere on the
edge-net that can reach the broker; co-located on the Pi 3A for the demo.

It also bridges dialects: keybow currently speaks bare strings ("press",
"r,g,b") while the relay node speaks contract JSON. The rule translates.
"""

import json

import paho.mqtt.client as mqtt

BROKER, PORT = "10.1.1.1", 1883

# button index (0..2)  ->  relay number (1..3)
BUTTON_RELAY = {0: 1, 1: 2, 2: 3}

TOPIC_BUTTON = "edge-net/keybow/button/{}"   # subscribe (keybow publishes bare "press")
TOPIC_LED    = "edge-net/keybow/led/{}"      # publish bare "r,g,b" (keybow's dialect)
TOPIC_RELAY  = "edge-net/automation/relay/{}"  # publish JSON {"state": ...}

LED_ON, LED_OFF = "0,255,0", "0,0,0"

# The rule holds the state, because neither dumb node does.
relay_on = {1: False, 2: False, 3: False}


def on_connect(client, userdata, flags, rc):
    print(f"Rule connected (rc={rc})")
    for b in BUTTON_RELAY:
        client.subscribe(TOPIC_BUTTON.format(b), qos=1)


def _pressed(payload):
    # Accept keybow's bare "press" and the contract's {"event":"press"}.
    p = payload.decode().strip()
    if p == "press":
        return True
    try:
        return json.loads(p).get("event") == "press"
    except ValueError:
        return False


def on_message(client, userdata, msg):
    for b, relay in BUTTON_RELAY.items():
        if msg.topic == TOPIC_BUTTON.format(b) and _pressed(msg.payload):
            relay_on[relay] = not relay_on[relay]
            state = "on" if relay_on[relay] else "off"
            # Command the relay (retained, so it restores on reboot — D4).
            client.publish(TOPIC_RELAY.format(relay),
                           json.dumps({"state": state}), qos=1, retain=True)
            # Reflect on the keybow LED (retained too).
            client.publish(TOPIC_LED.format(b),
                           LED_ON if relay_on[relay] else LED_OFF,
                           qos=1, retain=True)
            print(f"button {b} -> relay {relay} {state}")
            return


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_forever()
