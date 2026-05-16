from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont


class FramebufferDisplay:
    def __init__(self, config: Dict, state) -> None:
        self.config = config
        self.state = state
        self.width = int(config.get("display_width", 320))
        self.height = int(config.get("display_height", 240))
        self.fb = self._find_fb(config.get("framebuffer_candidates", ["/dev/fb1", "/dev/fb0"]))
        self.stop = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.last_activity = time.time()
        self.idle = False
        self.font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)

    def _find_fb(self, candidates) -> Optional[str]:
        for c in candidates:
            if os.path.exists(c) and os.access(c, os.W_OK):
                return c
        return None

    def start(self) -> None:
        if not self.fb:
            self.state.append_status("TFT framebuffer not available")
            return
        self.thread = threading.Thread(target=self._loop, name="tft-display", daemon=True)
        self.thread.start()
        self.state.append_status(f"LCD framebuffer active: {self.fb}")

    def close(self) -> None:
        self.stop.set()

    def wake(self) -> None:
        self.last_activity = time.time()
        self.idle = False

    def _write(self, img: Image.Image) -> None:
        img = img.convert("RGB").resize((self.width, self.height))
        # fb_ili9340 is RGB565 little endian.
        raw = bytearray()
        for r, g, b in img.getdata():
            v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            raw += int(v).to_bytes(2, "little")
        with open(self.fb, "wb", buffering=0) as f:
            f.write(raw)

    def _splash(self) -> Image.Image:
        path = Path(str(self.config.get("tft_screen_timeout_image", "/opt/morse-whisperer-pi/assets/horse_boot_splash.png")))
        if path.exists():
            return Image.open(path).convert("RGB").resize((self.width, self.height))
        img = Image.new("RGB", (self.width, self.height), "black")
        d = ImageDraw.Draw(img)
        d.text((22, 90), "The Morse\nWhisperer", fill=(80, 240, 255), font=self.font_big)
        return img

    def _screen(self, snap: Dict) -> Image.Image:
        q = snap.get("quality", {}) or {}
        dct = snap.get("decode", {}) or {}
        audio = snap.get("audio", {}) or {}
        copy = dct.get("copy") or dct.get("stable_copy") or "Waiting for CW..."
        raw = dct.get("raw") or dct.get("stable_raw") or "No accepted raw copy yet."
        if copy != "Waiting for CW...":
            self.last_activity = time.time()
        img = Image.new("RGB", (self.width, self.height), (3, 9, 14))
        d = ImageDraw.Draw(img)
        cyan = (70, 248, 255)
        orange = (255, 176, 46)
        muted = (145, 168, 184)
        d.rounded_rectangle((4, 4, self.width-5, self.height-5), radius=10, outline=(0, 95, 110), width=1)
        d.text((12, 10), "THE MORSE WHISPERER", fill=cyan, font=self.font_small)
        d.text((12, 30), f"Tone {q.get('selected_tone_hz','--')} Hz   WPM {float(q.get('wpm') or 0):.1f}", fill=orange, font=self.font_small)
        d.text((12, 58), str(copy)[-80:], fill=(220, 245, 255), font=self.font_big)
        d.text((12, 122), str(raw)[-120:], fill=muted, font=self.font)
        d.text((12, 202), f"SNR {float(q.get('snr_db') or 0):.1f} dB  RMS {float(audio.get('rms') or 0):.3f}", fill=muted, font=self.font_small)
        return img

    def _loop(self) -> None:
        while not self.stop.is_set():
            snap = self.state.snapshot()
            timeout = int(self.config.get("tft_screen_timeout_sec", 300))
            enabled = bool(self.config.get("tft_screen_timeout_enabled", True))
            if enabled and time.time() - self.last_activity > timeout:
                img = self._splash()
            else:
                img = self._screen(snap)
            try:
                self._write(img)
            except Exception as e:
                self.state.append_status(f"TFT write failed: {e}")
            time.sleep(float(self.config.get("display_refresh_sec", 1.0)))
