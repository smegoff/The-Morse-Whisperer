#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

CONFIG = Path("/opt/morse-whisperer-pi/config.json")
BASE_URL = "http://127.0.0.1:8080"

LCD_RESERVED = {22, 27}


def load_config():
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def post(path: str):
    req = urllib.request.Request(
        BASE_URL + path,
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"ERROR: {e}"


def setup_gpio():
    try:
        import RPi.GPIO as GPIO
    except Exception as e:
        raise SystemExit(f"RPi.GPIO unavailable: {e}")

    cfg = load_config()

    pins = {
        "page": int(cfg.get("button_page_gpio", 23)),
        "down": int(cfg.get("button_filter_down_gpio", 24)),
        "up": int(cfg.get("button_filter_up_gpio", 25)),
    }

    bad = [gpio for gpio in pins.values() if gpio in LCD_RESERVED]
    if bad:
        raise SystemExit(f"Refusing to use LCD GPIO pins: {bad}. GPIO22=LCD DC, GPIO27=LCD RESET.")

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for gpio in sorted(set(pins.values())):
        GPIO.setup(gpio, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    return GPIO, pins, cfg


def main():
    GPIO, pins, cfg = setup_gpio()

    poll = float(cfg.get("button_poll_sec", 0.06))
    debounce = float(cfg.get("button_debounce_sec", 0.25))

    actions = {
        "page": "/api/tft/next",
        "down": "/api/filter/down",
        "up": "/api/filter/up",
    }

    last_state = {name: 1 for name in pins}
    last_fire = {name: 0.0 for name in pins}

    print("Morse Whisperer button sidecar active")
    print(f"Page GPIO: {pins['page']} -> /api/tft/next")
    print(f"Down GPIO: {pins['down']} -> /api/filter/down")
    print(f"Up GPIO:   {pins['up']} -> /api/filter/up")

    while True:
        now = time.time()

        for name, gpio in pins.items():
            state = int(GPIO.input(gpio))

            # active-low button press
            if last_state[name] == 1 and state == 0:
                if now - last_fire[name] >= debounce:
                    print(f"{name} button pressed: {post(actions[name])}", flush=True)
                    last_fire[name] = now

            last_state[name] = state

        time.sleep(poll)


if __name__ == "__main__":
    main()
