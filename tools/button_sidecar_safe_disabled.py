#!/usr/bin/env python3
from __future__ import annotations

import time

print("Morse Whisperer button sidecar disabled for TFT safety.")
print("Reason: physical GPIO button mapping conflicts with LCD pins on XC9022/GoodTFT.")
print("GPIO22 = LCD DC, GPIO27 = LCD RESET. Do not use them for buttons.")

while True:
    time.sleep(3600)
