#!/usr/bin/env python3
from pathlib import Path
import os
import sys
import time

try:
    from PIL import Image
except Exception:
    sys.exit(0)


APP_DIR = Path("/opt/morse-whisperer-pi")
IMAGE_PATH = APP_DIR / "assets" / "boot_splash.png"

FB_CANDIDATES = [
    "/dev/fb1",
    "/dev/fb0",
]


def find_fb():
    for fb in FB_CANDIDATES:
        if os.path.exists(fb) and os.access(fb, os.W_OK):
            return fb
    return None


def rgb_to_rgb565_bytes(img):
    rgb = img.convert("RGB")
    data = bytearray()
    for r, g, b in rgb.getdata():
        value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data.append(value & 0xFF)
        data.append((value >> 8) & 0xFF)
    return data


def main():
    # This script must never prevent the main service from starting.
    try:
        fb = find_fb()
        if not fb:
            return 0

        if not IMAGE_PATH.exists():
            return 0

        img = Image.open(IMAGE_PATH).convert("RGB")
        img = img.resize((320, 240), Image.Resampling.LANCZOS)

        data = rgb_to_rgb565_bytes(img)

        with open(fb, "wb", buffering=0) as out:
            out.write(data)

        # Hold briefly so the image is visible before the main app redraws.
        time.sleep(2.5)
        return 0

    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
