#!/bin/bash
set -e

pip install paho-mqtt

sudo mkdir -p /opt/edge-net/sounds
sudo cp sounds/chime.wav /opt/edge-net/sounds/

sudo cp systemd/edge-net-audio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now edge-net-audio

sudo systemctl status edge-net-audio
