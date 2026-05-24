#!/usr/bin/env python3
from pathlib import Path
import os
import sys
import time
import math

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    sys.exit(0)

APP_DIR = Path("/opt/morse-whisperer-pi")
IMAGE_PATH = APP_DIR / "assets" / "horse_boot_splash.png"
FB_CANDIDATES = ["/dev/fb1", "/dev/fb0"]
W, H = 320, 240


def find_fb():
    for fb in FB_CANDIDATES:
        if os.path.exists(fb) and os.access(fb, os.W_OK):
            return fb
    return None


def load_font(size=10, bold=False):
    candidates = []
    if bold:
        candidates.append("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
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


def rgb565(img):
    rgb = img.convert("RGB")
    out = bytearray()
    for r, g, b in rgb.getdata():
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out.append(v & 0xFF)
        out.append((v >> 8) & 0xFF)
    return out


def frame(base, progress, tick):
    img = base.copy()
    draw = ImageDraw.Draw(img, "RGBA")

    # Small, clean overlay. Keep artwork visible.
    panel = (18, 200, 302, 236)
    draw.rounded_rectangle(panel, radius=8, fill=(0, 8, 12, 135), outline=(0, 220, 230, 75))

    dots = "." * ((tick % 4) + 1)
    label = f"BOOTING DECODER{dots}"
    f = load_font(9, bold=True)
    tw = draw.textlength(label, font=f)
    pulse = int(40 * math.sin(tick * 0.9))
    draw.text(((W - tw) / 2, 203), label, font=f, fill=(80, 255, 255, 195 + pulse))

    x, y = 30, 216
    bar_w, bar_h = 260, 8
    draw.rounded_rectangle((x, y, x + bar_w, y + bar_h), radius=4, fill=(0, 20, 24, 210), outline=(80, 255, 255, 170))

    segments = 18
    gap = 2
    inner_x = x + 5
    inner_w = bar_w - 10
    seg_w = (inner_w - gap * (segments - 1)) / segments
    filled = max(1, int(progress * segments))

    for i in range(segments):
        sx = int(inner_x + i * (seg_w + gap))
        ex = int(sx + seg_w)
        active = i < filled
        chase = max(0.0, 1.0 - abs(i - filled) / 2.5)

        if active:
            colour = (35, min(255, int(215 + 40 * chase)), 240, 230)
        else:
            colour = (10, 60, 65, 90)

        draw.rounded_rectangle((sx, y + 2, ex, y + bar_h - 2), radius=2, fill=colour)

    return img


def main():
    # Must never stop the appliance from starting.
    try:
        fb = find_fb()
        if not fb or not IMAGE_PATH.exists():
            return 0

        base = Image.open(IMAGE_PATH).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)

        # Keep this deliberately short. Full framebuffer writes are slow on the Pi TFT.
        frames = 12
        target_total_seconds = 2.6
        per_frame_delay = target_total_seconds / frames

        with open(fb, "wb", buffering=0) as out:
            for tick in range(frames):
                progress = (tick + 1) / frames
                img = frame(base, progress, tick)
                out.seek(0)
                out.write(rgb565(img))
                time.sleep(per_frame_delay)

            # Brief final hold so 100% is visible before main display takes over.
            out.seek(0)
            out.write(rgb565(frame(base, 1.0, frames)))
            time.sleep(0.35)

        return 0

    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
