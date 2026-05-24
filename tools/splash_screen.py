#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


APP_DIR = Path("/opt/morse-whisperer-pi")
CONFIG = APP_DIR / "config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except Exception:
        return {}


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    ]
    for f in candidates:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def measure(draw, text, f):
    try:
        b = draw.textbbox((0, 0), text, font=f)
        return b[2] - b[0], b[3] - b[1]
    except Exception:
        return len(text) * 8, 14


def write_fb(img: Image.Image, fb_path: str, width: int, height: int, rotate: int) -> None:
    if rotate:
        img = img.rotate(rotate, expand=True)
        img = img.resize((width, height))

    rgb = img.convert("RGB")
    data = bytearray()

    for r, g, b in rgb.getdata():
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data.append(v & 0xFF)
        data.append((v >> 8) & 0xFF)

    with open(fb_path, "wb", buffering=0) as fb:
        fb.write(data)


def draw_splash(width: int, height: int, progress: float, cfg: dict) -> Image.Image:
    bg = (4, 8, 14)
    panel = (10, 18, 30)
    panel2 = (14, 24, 40)
    line = (45, 100, 180)
    text = (235, 245, 255)
    muted = (145, 165, 185)
    blue = (90, 190, 255)
    green = (80, 255, 170)
    yellow = (255, 220, 90)

    f_title = font(24, True)
    f_sub = font(14, True)
    f_small = font(11, False)
    f_tiny = font(10, False)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((8, 8, width - 8, height - 8), radius=14, fill=panel, outline=line)
    draw.rounded_rectangle((11, 11, width - 11, height - 11), radius=12, outline=(20, 55, 95))

    title1 = "THE MORSE"
    title2 = "WHISPERER"
    tw, _ = measure(draw, title1, f_title)
    draw.text(((width - tw) // 2, 22), title1, font=f_title, fill=text)
    tw, _ = measure(draw, title2, f_title)
    draw.text(((width - tw) // 2, 48), title2, font=f_title, fill=blue)

    # Little radio/fox icon.
    cx, cy = width // 2, 110
    draw.rounded_rectangle((116, 76, 204, 144), radius=12, fill=panel2, outline=blue)
    draw.polygon([(cx - 30, cy - 8), (cx - 14, cy - 32), (cx - 8, cy - 4)], fill=(210, 220, 235), outline=(80, 120, 170))
    draw.polygon([(cx + 30, cy - 8), (cx + 14, cy - 32), (cx + 8, cy - 4)], fill=(210, 220, 235), outline=(80, 120, 170))
    draw.polygon([(cx - 32, cy - 6), (cx, cy - 24), (cx + 32, cy - 6), (cx + 20, cy + 24), (cx, cy + 34), (cx - 20, cy + 24)], fill=(185, 195, 215), outline=(80, 120, 170))
    draw.polygon([(cx - 14, cy + 6), (cx, cy + 30), (cx + 14, cy + 6)], fill=(235, 240, 248))
    draw.ellipse((cx - 18, cy - 2, cx - 10, cy + 6), fill=(10, 18, 30))
    draw.ellipse((cx + 10, cy - 2, cx + 18, cy + 6), fill=(10, 18, 30))
    draw.ellipse((cx - 4, cy + 8, cx + 4, cy + 14), fill=(20, 28, 38))

    draw.text((26, 154), "CW DECODER APPLIANCE", font=f_small, fill=muted)
    draw.text((26, 170), "AUTO TONE  ·  LIVE COPY  ·  WEB UI", font=f_tiny, fill=blue)

    port = int(cfg.get("web_port", 8080))
    url = f"http://{local_ip()}:{port}"
    draw.text((26, 186), url, font=f_small, fill=green)

    bar_x, bar_y, bar_w, bar_h = 26, 210, width - 52, 10
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=5, fill=(6, 12, 20), outline=(50, 80, 110))
    fill_w = int(bar_w * max(0, min(1, progress)))
    if fill_w:
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=5, fill=blue)

    msg = "INITIALISING DECODER..."
    mw, _ = measure(draw, msg, f_tiny)
    draw.text(((width - mw) // 2, 224), msg, font=f_tiny, fill=yellow)

    return img


def main() -> int:
    cfg = load_config()

    if not bool(cfg.get("systemd_splash_enabled", True)):
        return 0

    width = int(cfg.get("display_width", 320))
    height = int(cfg.get("display_height", 240))
    rotate = int(cfg.get("display_rotate", 0))
    seconds = float(cfg.get("systemd_splash_seconds", 4.0) or 4.0)

    fb_path = None
    for candidate in cfg.get("framebuffer_candidates", ["/dev/fb1", "/dev/fb0"]):
        if os.path.exists(candidate) and os.access(candidate, os.W_OK):
            fb_path = candidate
            break

    if not fb_path:
        print("No writable framebuffer found; skipping splash", file=sys.stderr)
        return 0

    # Hard safety cap: this script must always exit.
    seconds = max(0.5, min(seconds, 10.0))
    frames = max(6, int(seconds * 6))
    start = time.time()

    for i in range(frames + 1):
        progress = i / frames
        img = draw_splash(width, height, progress, cfg)
        write_fb(img, fb_path, width, height, rotate)

        remaining = seconds - (time.time() - start)
        if i < frames and remaining > 0:
            time.sleep(min(remaining / max(1, frames - i), 0.18))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
