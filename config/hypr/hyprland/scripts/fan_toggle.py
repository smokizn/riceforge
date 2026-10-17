#!/usr/bin/env python3

import subprocess

subprocess.run(
    ["sudo", "-n", "/usr/local/bin/fan-toggle"],
    check=True
)