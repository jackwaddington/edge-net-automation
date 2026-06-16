BROKER = "10.1.1.1"
PORT   = 1883

# This node subscribes — relay commands, one per relay (1..3).
# Payload is JSON: {"state": "on"} or {"state": "off"}  (contract D2).
TOPIC_RELAY  = "edge-net/automation/relay/{}"   # .format(n) for n in 1,2,3

# Liveness (contract D3): retained, with an LWT registered on connect.
TOPIC_STATUS = "edge-net/automation/status"

RELAYS = (1, 2, 3)
