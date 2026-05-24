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
CONFIG_PATH = APP_DIR / "config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.4)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def load_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates.extend([
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        ])
    candidates.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    ])
    for f in candidates:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def measure(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    try:
        b = draw.textbbox((0, 0), text, font=font)
        return b[2] - b[0], b[3] - b[1]
    except Exception:
        return max(1, len(text) * 8), 14


def clip(draw: ImageDraw.ImageDraw, value: str, font, max_w: int) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    w, _ = measure(draw, value, font)
    if w <= max_w:
        return value

    suffix = "..."
    while value:
        trial = value + suffix
        w, _ = measure(draw, trial, font)
        if w <= max_w:
            return trial
        value = value[:-1]
    return suffix


def find_fb(cfg: dict) -> str | None:
    for candidate in cfg.get("framebuffer_candidates", ["/dev/fb1", "/dev/fb0"]):
        if os.path.exists(candidate) and os.access(candidate, os.W_OK):
            return candidate
    return None


def write_fb(img: Image.Image, fb_path: str, width: int, height: int, rotate: int) -> None:
    if rotate:
        img = img.rotate(rotate, expand=True)
        img = img.resize((width, height))

    rgb = img.convert("RGB")
    data = bytearray()

    # RGB888 to RGB565 little endian for fbtft.
    for r, g, b in rgb.getdata():
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data.append(v & 0xFF)
        data.append((v >> 8) & 0xFF)

    with open(fb_path, "wb", buffering=0) as f:
        f.write(data)


def draw_splash(width: int, height: int, cfg: dict, progress: float) -> Image.Image:
    bg = (4, 8, 14)
    panel = (9, 18, 30)
    panel2 = (14, 28, 48)
    line = (55, 120, 210)
    faint = (22, 52, 90)
    text = (238, 248, 255)
    muted = (145, 170, 190)
    blue = (85, 190, 255)
    cyan = (90, 255, 245)
    green = (80, 255, 170)
    amber = (255, 220, 90)

    title_font = load_font(23, bold=True)
    title_font2 = load_font(26, bold=True)
    mid_font = load_font(14, bold=True)
    small_font = load_font(11)
    tiny_font = load_font(10)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Outer frame.
    draw.rounded_rectangle((7, 7, width - 7, height - 7), radius=15, fill=panel, outline=line)
    draw.rounded_rectangle((11, 11, width - 11, height - 11), radius=12, outline=faint)

    # Tiny signal/grid styling.
    for x in range(22, width - 20, 24):
        draw.line((x, 200, x + 10, 200), fill=(18, 45, 70))
    for y in (38, 74, 150, 204):
        draw.line((18, y, width - 18, y), fill=(10, 30, 50))

    title = str(cfg.get("systemd_splash_title", "THE MORSE WHISPERER"))
    subtitle = str(cfg.get("systemd_splash_subtitle", "CW Decoder Appliance"))

    # Split title if needed.
    line1 = "THE MORSE"
    line2 = "WHISPERER"
    if len(title) <= 18:
        line1 = title
        line2 = ""

    w1, _ = measure(draw, line1, title_font)
    draw.text(((width - w1) // 2, 20), line1, font=title_font, fill=text)

    if line2:
        w2, _ = measure(draw, line2, title_font2)
        draw.text(((width - w2) // 2, 45), line2, font=title_font2, fill=blue)

    # Icon panel.
    icon_x1, icon_y1, icon_x2, icon_y2 = 112, 78, 208, 145
    draw.rounded_rectangle((icon_x1, icon_y1, icon_x2, icon_y2), radius=13, fill=panel2, outline=blue)

    # Stylised "whisper fox / radio" mark.
    cx, cy = width // 2, 112
    draw.polygon([(cx - 34, cy - 6), (cx - 15, cy - 34), (cx - 9, cy - 2)], fill=(205, 218, 236), outline=(70, 130, 190))
    draw.polygon([(cx + 34, cy - 6), (cx + 15, cy - 34), (cx + 9, cy - 2)], fill=(205, 218, 236), outline=(70, 130, 190))
    draw.polygon(
        [(cx - 34, cy - 5), (cx, cy - 25), (cx + 34, cy - 5), (cx + 22, cy + 23), (cx, cy + 35), (cx - 22, cy + 23)],
        fill=(178, 198, 224),
        outline=(70, 130, 190),
    )
    draw.polygon([(cx - 14, cy + 5), (cx, cy + 31), (cx + 14, cy + 5)], fill=(238, 245, 250))
    draw.ellipse((cx - 18, cy - 3, cx - 10, cy + 5), fill=(5, 14, 25))
    draw.ellipse((cx + 10, cy - 3, cx + 18, cy + 5), fill=(5, 14, 25))
    draw.ellipse((cx - 4, cy + 8, cx + 4, cy + 14), fill=(5, 14, 25))

    # Radio waves.
    draw.arc((cx - 58, cy - 24, cx - 26, cy + 28), 105, 255, fill=cyan, width=2)
    draw.arc((cx + 26, cy - 24, cx + 58, cy + 28), -75, 75, fill=cyan, width=2)

    # Text.
    subtitle = clip(draw, subtitle, mid_font, width - 52)
    sw, _ = measure(draw, subtitle, mid_font)
    draw.text(((width - sw) // 2, 154), subtitle, font=mid_font, fill=muted)

    tagline = "AUTO TONE  ·  LIVE COPY  ·  WEB UI"
    tw, _ = measure(draw, tagline, tiny_font)
    draw.text(((width - tw) // 2, 174), tagline, font=tiny_font, fill=blue)

    url = f"http://{local_ip()}:{int(cfg.get('web_port', 8080))}"
    url = clip(draw, url, small_font, width - 50)
    uw, _ = measure(draw, url, small_font)
    draw.text(((width - uw) // 2, 188), url, font=small_font, fill=green)

    # Progress bar.
    bar_x, bar_y, bar_w, bar_h = 26, 210, width - 52, 10
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=5, fill=(4, 10, 18), outline=(55, 85, 120))

    fill_w = int(bar_w * max(0.0, min(1.0, progress)))
    if fill_w > 0:
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=5, fill=blue)

    msg = "INITIALISING DECODER..."
    mw, _ = measure(draw, msg, tiny_font)
    draw.text(((width - mw) // 2, 224), msg, font=tiny_font, fill=amber)

    return img


def main() -> int:
    cfg = load_config()

    if not bool(cfg.get("systemd_splash_enabled", True)):
        return 0

    width = int(cfg.get("display_width", 320))
    height = int(cfg.get("display_height", 240))
    rotate = int(cfg.get("display_rotate", 0))
    seconds = float(cfg.get("systemd_splash_seconds", 3.5) or 3.5)

    # Hard bounds. This must never become a boot blocker.
    seconds = max(0.5, min(seconds, 5.0))

    fb = find_fb(cfg)
    if not fb:
        print("safe_splash: no framebuffer found; skipping", file=sys.stderr)
        return 0

    # Hard deadline independent of frame count.
    deadline = time.monotonic() + seconds
    frames = max(4, int(seconds * 7))

    for i in range(frames + 1):
        now = time.monotonic()
        if now >= deadline:
            break

        progress = min(1.0, i / max(1, frames))
        img = draw_splash(width, height, cfg, progress)
        write_fb(img, fb, width, height, rotate)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        time.sleep(min(0.12, remaining))

    # Draw one final complete frame, then exit immediately.
    try:
        img = draw_splash(width, height, cfg, 1.0)
        write_fb(img, fb, width, height, rotate)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"safe_splash failed: {e}", file=sys.stderr)
        raise SystemExit(0)
