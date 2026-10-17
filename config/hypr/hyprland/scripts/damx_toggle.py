#!/usr/bin/env python3
import socket
import json
import os
import subprocess

SOCKET_PATH = "/var/run/DAMX.sock"
FLAG_FILE = "/tmp/fan_is_max"


def send_notification(title, message):
    subprocess.run(["notify-send", title, message])


def send_command(command, params):
    if not os.path.exists(SOCKET_PATH):
        return
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(SOCKET_PATH)
    data = {"command": command, "params": params}
    client.send(json.dumps(data).encode())
    client.close()


if os.path.exists(FLAG_FILE):
    #Auto
    send_command("set_fan_speed", {"cpu": 0, "gpu": 0})
    send_notification("Fan Speed", "Automatic")
    os.remove(FLAG_FILE)
    
else:
    #Max
    send_notification("Fan Speed", "Maximum")
    with open(FLAG_FILE, "w") as f: f.write("1")
    send_command("set_fan_speed", {"cpu": 100, "gpu": 100})
   
