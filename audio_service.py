"""Edge-NET hub audio service.

Subscribes to edge/hub/audio/play and plays sounds or TTS on the Pi 3A's
audio jack. Messages are queued — no overlapping audio.

Install:
    pip install paho-mqtt
    sudo apt install espeak              # TTS fallback (always available)
    sudo apt install piper piper-voices  # TTS preferred; falls back to espeak

Deploy:
    sudo cp systemd/edge-net-audio.service /etc/systemd/system/
    sudo systemctl enable --now edge-net-audio

Test:
    mosquitto_pub -h 10.1.1.1 -t edge/hub/audio/play -m '{"tts":"hello world"}'
    mosquitto_pub -h 10.1.1.1 -t edge/hub/audio/play -m '{"file":"chime.wav"}'
    mosquitto_pub -h 10.1.1.1 -t edge/hub/audio/play -m '{"volume":70}'
"""

import json
import os
import queue
import subprocess
import threading

import paho.mqtt.client as mqtt

BROKER, PORT     = "10.1.1.1", 1883
CLIENT_ID        = "hub-audio"
SOUNDS_DIR       = "/opt/edge-net/sounds"
TOPIC_PLAY       = "edge/hub/audio/play"
TOPIC_STATE      = "edge/hub/audio/state"

# Piper model path — adjust if installed to a non-default location.
PIPER_MODEL      = "/usr/share/piper/voices/en_US-lessac-medium.onnx"

_queue  = queue.Queue()
_client = None       # set after connect; worker reads this to publish state


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _play_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp3":
        subprocess.run(["mpg123", "-q", path], check=False)
    else:
        subprocess.run(["aplay", "-q", path], check=False)


def _speak(text):
    if os.path.exists(PIPER_MODEL):
        proc = subprocess.Popen(
            ["piper", "--model", PIPER_MODEL, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        aplay = subprocess.Popen(
            ["aplay", "-q", "-r", "22050", "-f", "S16_LE", "-c", "1"],
            stdin=proc.stdout,
        )
        proc.stdin.write(text.encode())
        proc.stdin.close()
        proc.wait()
        aplay.wait()
    else:
        subprocess.run(["espeak", "-s", "110", text], check=False)


def _set_volume(level):
    pct = max(0, min(100, int(level)))
    subprocess.run(
        ["amixer", "sset", "Master", f"{pct}%"],
        check=False, capture_output=True,
    )
    print(f"Volume set to {pct}%")


# ---------------------------------------------------------------------------
# Worker thread — drains the queue sequentially
# ---------------------------------------------------------------------------

def _worker():
    while True:
        item = _queue.get()
        if item is None:
            break

        source = None
        try:
            if "volume" in item:
                _set_volume(item["volume"])
                _queue.task_done()
                continue

            if "file" in item:
                source = item["file"]
                path = os.path.join(SOUNDS_DIR, source)
                _publish_state("playing", source)
                print(f"Playing file: {path}")
                _play_file(path)

            elif "tts" in item:
                source = item["tts"][:60]
                _publish_state("playing", source)
                print(f"TTS: {source}")
                _speak(item["tts"])

        except Exception as exc:
            print(f"Audio error: {exc}")
        finally:
            _publish_state("idle", None)
            _queue.task_done()


def _publish_state(status, source):
    if _client is None:
        return
    payload = {"status": status}
    if source:
        payload["source"] = source
    _client.publish(TOPIC_STATE, json.dumps(payload), qos=1, retain=True)


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def on_connect(client, userdata, flags, rc):
    print(f"Audio service connected (rc={rc})")
    client.subscribe(TOPIC_PLAY, qos=1)
    _publish_state("idle", None)


def on_message(client, userdata, msg):
    try:
        item = json.loads(msg.payload.decode())
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"Bad payload on {msg.topic}: {exc}")
        return
    print(f"Queued: {item}")
    _queue.put(item)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

thread = threading.Thread(target=_worker, daemon=True)
thread.start()

_client = mqtt.Client(client_id=CLIENT_ID)
_client.on_connect = on_connect
_client.on_message = on_message
_client.will_set(
    "edge-net/automation/status",
    json.dumps({"status": "offline"}),
    qos=1, retain=True,
)
_client.connect(BROKER, PORT)
_client.loop_forever()
