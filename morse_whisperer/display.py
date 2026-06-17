from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class FramebufferDisplay:
    PAGES = ["COPY", "STATUS", "RAW", "SETTINGS", "TRAINER"]

    def __init__(self, config, state):
        self.config = config
        self.state = state
        self.enabled = bool(config.get("display_enabled", True))
        self.width = int(config.get("display_width", 320))
        self.height = int(config.get("display_height", 240))
        self.rotate = int(config.get("display_rotate", 0))
        self.refresh = float(config.get("display_refresh_sec", 1.0))
        self.fb_path = self.find_fb()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.frozen_img: Optional[Image.Image] = None
        self._last_tft_next_page_counter = 0
        self._last_tft_freeze_counter = 0
        self.splash_enabled = bool(config.get("splash_enabled", True))
        self.splash_seconds = float(config.get("splash_seconds", 4.0))
        self.splash_until = time.time() + self.splash_seconds if self.splash_enabled else 0.0

        self.page = str(config.get("tft_default_page", "COPY")).upper()
        if self.page not in self.PAGES:
            self.page = "COPY"

        self.font_huge = self.load_font(30, bold=True)
        self.font_big = self.load_font(26, bold=True)
        self.font_mid = self.load_font(18, bold=True)
        self.font = self.load_font(14, bold=False)
        self.font_small = self.load_font(11, bold=False)
        self.font_tiny = self.load_font(10, bold=False)

    def load_font(self, size: int, bold: bool = False):
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

    def find_fb(self) -> Optional[str]:
        for candidate in self.config.get("framebuffer_candidates", ["/dev/fb1", "/dev/fb0"]):
            if os.path.exists(candidate) and os.access(candidate, os.W_OK):
                return candidate
        return None

    def start(self):
        if not self.enabled:
            return
        if not self.fb_path:
            self.state.append_status("LCD framebuffer not found/writable")
            return
        self.state.append_status(f"LCD framebuffer active: {self.fb_path}")
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def next_page(self):
        idx = self.PAGES.index(self.page) if self.page in self.PAGES else 0
        self.page = self.PAGES[(idx + 1) % len(self.PAGES)]
        self.frozen_img = None
        self.state.append_status(f"TFT page: {self.page}")

    def toggle_freeze(self):
        if self.frozen_img is None:
            self.frozen_img = self.draw_screen()
            self.state.append_status("TFT display frozen")
        else:
            self.frozen_img = None
            self.state.append_status("TFT display unfrozen")

    def check_control_requests(self):
        try:
            snap = self.state.snapshot()
            control = snap.get("control", {}) if isinstance(snap, dict) else {}
            if not isinstance(control, dict):
                return

            next_counter = int(control.get("tft_next_page_counter", 0) or 0)
            freeze_counter = int(control.get("tft_freeze_counter", 0) or 0)

            if next_counter > self._last_tft_next_page_counter:
                self._last_tft_next_page_counter = next_counter
                self.next_page()

            if freeze_counter > self._last_tft_freeze_counter:
                self._last_tft_freeze_counter = freeze_counter
                self.toggle_freeze()

        except Exception as e:
            self.state.append_status(f"TFT control request failed: {e}")

    def measure_text(self, draw, text: str, font):
        sample = text if text else "Ag"
        try:
            bbox = draw.textbbox((0, 0), sample, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return max(1, len(sample) * 8), 14

    def clip_to_width(self, draw, value: str, font, max_w: int) -> str:
        value = str(value or "").strip()
        if not value:
            return ""
        tw, _ = self.measure_text(draw, value, font)
        if tw <= max_w:
            return value
        suffix = "..."
        while value:
            trial = value + suffix
            tw, _ = self.measure_text(draw, trial, font)
            if tw <= max_w:
                return trial
            value = value[:-1]
        return suffix

    def break_long_word(self, draw, word: str, font, max_width: int):
        parts = []
        current = ""
        for ch in word:
            test = current + ch
            tw, _ = self.measure_text(draw, test, font)
            if tw <= max_width or not current:
                current = test
            else:
                parts.append(current)
                current = ch
        if current:
            parts.append(current)
        return parts

    def wrap_text(self, draw, text: str, font, max_width: int, max_lines: int):
        words = (text or "").split()
        if not words:
            return []
        lines = []
        cur = ""
        for w in words:
            test = w if not cur else cur + " " + w
            tw, _ = self.measure_text(draw, test, font)
            if tw <= max_width:
                cur = test
                continue
            if cur:
                lines.append(cur)
                cur = ""
            ww, _ = self.measure_text(draw, w, font)
            if ww > max_width:
                pieces = self.break_long_word(draw, w, font, max_width)
                for piece in pieces[:-1]:
                    lines.append(piece)
                cur = pieces[-1]
            else:
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines:
            return lines
        lines = lines[:max_lines]
        while lines:
            trial = lines[-1] + "..."
            tw, _ = self.measure_text(draw, trial, font)
            if tw <= max_width:
                lines[-1] = trial
                break
            lines[-1] = lines[-1][:-1]
            if not lines[-1]:
                lines[-1] = "..."
                break
        return lines

    def fit_text_box(self, draw, text: str, box_w: int, box_h: int, max_size: int = 28, min_size: int = 14, max_lines: int = 4, bold: bool = True):
        fallback_font = self.load_font(min_size, bold=bold)
        fallback_lines = self.wrap_text(draw, text, fallback_font, box_w, max_lines)
        _, fallback_line_h = self.measure_text(draw, "Ag", fallback_font)
        fallback_gap = max(2, int(min_size * 0.15))

        for size in range(max_size, min_size - 1, -1):
            font = self.load_font(size, bold=bold)
            lines = self.wrap_text(draw, text, font, box_w, max_lines)
            _, line_h = self.measure_text(draw, "Ag", font)
            gap = max(2, int(size * 0.15))
            total_h = (len(lines) * line_h) + (max(0, len(lines) - 1) * gap)
            if total_h <= box_h:
                return font, lines, line_h, gap

        return fallback_font, fallback_lines, fallback_line_h, fallback_gap

    def level_colour(self, level: str):
        if level == "GOOD":
            return (60, 255, 140)
        if level in ("LOW", "HOT"):
            return (255, 210, 90)
        if level in ("IDLE", "CLIP"):
            return (255, 90, 90)
        return (150, 165, 180)

    def bar(self, draw, xy, value, colour):
        x, y, w, h = xy
        value = max(0.0, min(1.0, float(value)))
        draw.rounded_rectangle((x, y, x + w, y + h), radius=3, fill=(15, 22, 30), outline=(55, 70, 85))
        draw.rounded_rectangle((x, y, x + int(w * value), y + h), radius=3, fill=colour)

    def draw_header(self, draw, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours
        draw.rounded_rectangle((4, 4, self.width - 4, 34), radius=8, fill=panel, outline=line)
        draw.text((12, 9), "The Morse Whisperer", font=self.font_mid, fill=text)

        page_w, _ = self.measure_text(draw, self.page, self.font_small)
        draw.text((self.width - 12 - page_w, 10), self.page, font=self.font_small, fill=blue)

    def draw_button_bar(self, draw, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours

        # Touch soft-key bar. The old four-button sidecar used LCD pins on
        # some builds, so the app now treats these labels as screen regions.
        draw.rounded_rectangle((4, 200, self.width - 4, self.height - 4), radius=8, fill=(8, 13, 18), outline=line)

        # Compact hold legend. Keep it inside the footer so it does not
        # trample the COPY/RAW panels.
        hint_left = "HOLD: 1 FRZ   2 RST"
        hint_right = "3 FULL   4 FULL"
        draw.text((12, 204), hint_left, font=self.font_tiny, fill=muted)

        right_w, _ = self.measure_text(draw, hint_right, self.font_tiny)
        draw.text((self.width - 12 - right_w, 204), hint_right, font=self.font_tiny, fill=muted)

        left = 8
        gap = 4
        top = 216
        bottom = self.height - 6
        total_w = self.width - (left * 2)
        box_w = (total_w - (gap * 3)) // 4
        box_h = bottom - top

        active_button = ""
        active_label = ""

        try:
            active_path = Path("/run/morse-whisperer-button.json")
            if active_path.exists():
                active_data = json.loads(active_path.read_text())
                if float(active_data.get("until", 0.0) or 0.0) >= time.time():
                    active_button = str(active_data.get("button", "") or "")
                    active_label = str(active_data.get("label", "") or "").upper()
        except Exception:
            active_button = ""
            active_label = ""

        buttons = [
            ("1", "PAGE",  blue),
            ("2", "SCAN",  yellow),
            ("3", "RESET", red),
            ("4", "CLEAR", green),
        ]

        for idx, (num, label, accent) in enumerate(buttons):
            x1 = left + idx * (box_w + gap)
            x2 = x1 + box_w

            is_active = (str(num) == str(active_button))

            border = (245, 250, 255) if is_active else accent
            fill = (42, 54, 74) if is_active else (10, 18, 28)
            label_colour = (255, 255, 255) if is_active else accent

            draw.rectangle((x1, top, x2, bottom), outline=border, fill=fill)

            if is_active:
                # Inner accent line makes the active key obvious on the small TFT.
                draw.rectangle((x1 + 2, top + 2, x2 - 2, bottom - 2), outline=accent)

            # Combined label inside the button: "1 PAGE", "2 SCAN", etc.
            combined = f"{num} {label}"
            label_font = self.font_small

            # RESET/CLEAR can be a little wide on the 320px footer, so fall
            # back to the tiny font per button rather than changing layout.
            tw, th = self.measure_text(draw, combined, label_font)
            if tw > box_w - 8:
                label_font = self.font_tiny
                tw, th = self.measure_text(draw, combined, label_font)

            tx = x1 + max(0, (box_w - tw) // 2)
            ty = top + max(0, (box_h - th) // 2) - 1

            draw.text((tx, ty), combined, font=label_font, fill=label_colour)

    def draw_copy_page(self, draw, snap, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours
        dec = snap.get("decode", {}) or {}
        q = snap.get("quality", {}) or {}
        a = snap.get("audio", {}) or {}
        cfg = snap.get("config", {}) or {}

        copy = (dec.get("stable_copy") or dec.get("copy") or "").strip()

        # MW_TFT_DECODER_PROFILE_LABEL_V1
        profile = str(cfg.get("decoder_profile") or "clean").strip().lower()
        if profile in ("kiwi", "radio", "radio_cw"):
            profile_label = "RADIO"
        else:
            profile_label = "CLEAN"
        copy_label = f"STABLE COPY {profile_label}"

        # Main copy panel
        draw.rounded_rectangle((4, 40, self.width - 4, 140), radius=10, fill=panel2, outline=line)
        draw.text((12, 46), copy_label, font=self.font_small, fill=muted)

        ip = local_ip()
        port = int(cfg.get("web_port", 8080))
        web_url = f"http://{ip}:{port}"

        label_w, _ = self.measure_text(draw, copy_label, self.font_small)
        url_left_min = 12 + label_w + 12
        url_right_margin = 22
        url_right = self.width - url_right_margin
        url_max_w = max(60, url_right - url_left_min)
        web_url = self.clip_to_width(draw, web_url, self.font_small, url_max_w)
        url_w, _ = self.measure_text(draw, web_url, self.font_small)
        url_x = max(url_left_min, url_right - url_w)
        draw.text((url_x, 46), web_url, font=self.font_small, fill=blue)

        if copy:
            copy_x = 12
            copy_y = 62
            copy_w = self.width - 24
            copy_h = 64

            fit_font, lines, line_h, gap = self.fit_text_box(
                draw, copy, copy_w, copy_h, max_size=28, min_size=13, max_lines=4, bold=True
            )
            total_h = (len(lines) * line_h) + (max(0, len(lines) - 1) * gap)
            y = copy_y + max(0, (copy_h - total_h) // 2)
            for ln in lines:
                draw.text((copy_x, y), ln, font=fit_font, fill=text)
                y += line_h + gap
        else:
            draw.text((12, 80), "Waiting for CW...", font=self.font_big, fill=(95, 110, 125))

        tone = q.get("live_tone_lock_hz") or q.get("selected_tone_hz") or cfg.get("target_tone_hz") or "--"
        wpm = float(q.get("wpm") or 0)
        snr = float(q.get("snr_db") or 0)
        conf = float(q.get("confidence") or 0)
        level = str(a.get("level_status") or "--")

        # Metrics panel
        draw.rounded_rectangle((4, 146, self.width - 4, 200), radius=10, fill=panel, outline=line)
        draw.text((12, 152), "TONE", font=self.font_small, fill=muted)
        draw.text((12, 167), f"{tone} Hz", font=self.font_mid, fill=blue)

        draw.text((102, 152), "WPM", font=self.font_small, fill=muted)
        draw.text((102, 167), f"{wpm:.1f}", font=self.font_mid, fill=text)

        draw.text((168, 152), "AUDIO", font=self.font_small, fill=muted)
        draw.text((168, 167), level, font=self.font_mid, fill=self.level_colour(level))

        draw.text((258, 152), "SNR", font=self.font_small, fill=muted)
        snr_colour = green if snr >= 12 else yellow if snr >= 5 else red
        draw.text((258, 167), f"{snr:.1f}", font=self.font_mid, fill=snr_colour)

        self.bar(draw, (12, 190, 140, 5), min(max((snr + 5) / 50, 0), 1), snr_colour)
        self.bar(draw, (172, 190, 136, 5), conf, green if conf >= 0.85 else yellow if conf >= 0.45 else red)

        self.draw_button_bar(draw, colours)

    def draw_status_page(self, draw, snap, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours
        q = snap.get("quality", {}) or {}
        a = snap.get("audio", {}) or {}
        cfg = snap.get("config", {}) or {}

        draw.rounded_rectangle((4, 40, self.width - 4, 200), radius=10, fill=panel2, outline=line)
        draw.text((12, 48), "STATUS", font=self.font_mid, fill=text)

        rows = [
            ("Tone lock", f"{q.get('live_tone_lock_hz') or q.get('selected_tone_hz') or '--'} Hz"),
            ("Tone mode", str(cfg.get("tone_mode") or q.get("tone_mode") or "--")),
            ("Squelch", "OPEN" if q.get("squelch_open") else "closed"),
            ("Reason", str(q.get("reason") or "--")),
            ("WPM", f"{float(q.get('wpm') or 0):.1f}"),
            ("SNR", f"{float(q.get('snr_db') or 0):.1f} dB"),
            ("Confidence", f"{float(q.get('confidence') or 0):.2f}"),
            ("Audio", str(a.get("level_status") or "--")),
            ("RMS/Peak", f"{float(a.get('rms') or 0):.3f}/{float(a.get('peak') or 0):.3f}"),
            ("Buffer", f"{float(a.get('buffered_seconds') or 0):.1f}s"),
        ]

        y = 74
        for k, v in rows:
            draw.text((12, y), k, font=self.font_small, fill=muted)
            val = self.clip_to_width(draw, v, self.font_small, 180)
            draw.text((122, y), val, font=self.font_small, fill=text)
            y += 12

        self.draw_button_bar(draw, colours)

    def draw_raw_page(self, draw, snap, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours
        dec = snap.get("decode", {}) or {}
        raw = (dec.get("stable_raw") or dec.get("raw") or "").strip()

        draw.rounded_rectangle((4, 40, self.width - 4, 200), radius=10, fill=panel2, outline=line)
        draw.text((12, 48), "RAW", font=self.font_mid, fill=text)

        if not raw:
            draw.text((12, 96), "No accepted raw copy yet.", font=self.font_mid, fill=(95, 110, 125))
        else:
            lines = self.wrap_text(draw, raw, self.font, self.width - 24, 8)
            y = 76
            for ln in lines:
                draw.text((12, y), ln, font=self.font, fill=text)
                y += 16

        self.draw_button_bar(draw, colours)


    def draw_settings_page(self, draw, snap, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours
        cfg = snap.get("config", {}) or {}
        q = snap.get("quality", {}) or {}

        draw.rounded_rectangle((4, 40, self.width - 4, 200), radius=10, fill=panel2, outline=line)
        draw.text((12, 48), "SETTINGS", font=self.font_mid, fill=text)

        rows = [
            ("Mode", str(cfg.get("tone_mode") or "--")),
            ("Tone", f"{cfg.get('target_tone_hz', '--')} Hz"),
            ("WPM hint", f"{float(cfg.get('initial_wpm') or 0):.2f}"),
            ("Word gap", f"{float(cfg.get('word_gap_units') or 0):.2f}u"),
            ("Input", f"{cfg.get('input_capture_percent', '--')}%"),
            ("LCD", f"{cfg.get('lcd_brightness_percent', '--')}%"),
            ("Output", str(cfg.get("audio_output_device") or "--")),
            ("Gen", f"{cfg.get('cw_generator_tone_hz', cfg.get('target_tone_hz', 700))} Hz / {cfg.get('cw_generator_wpm', cfg.get('initial_wpm', 18.75))} WPM"),
            ("Live lock", f"{q.get('live_tone_lock_hz') or q.get('selected_tone_hz') or '--'} Hz"),
        ]

        y = 74
        for k, v in rows:
            draw.text((12, y), k, font=self.font_small, fill=muted)
            val = self.clip_to_width(draw, v, self.font_small, 186)
            draw.text((112, y), val, font=self.font_small, fill=text)
            y += 13

        self.draw_button_bar(draw, colours)



    def draw_trainer_page(self, draw, snap, colours):
        bg, panel, panel2, line, text, muted, green, blue, yellow, red = colours

        result = snap.get("trainer_selftest", {}) or {}
        cfg = snap.get("config", {}) or {}

        status = str(result.get("status") or "NOT RUN")
        if status == "PASS":
            status_colour = green
        elif status == "CLOSE":
            status_colour = yellow
        elif status == "FAIL":
            status_colour = red
        else:
            status_colour = muted

        draw.rounded_rectangle((4, 40, self.width - 4, 204), radius=10, fill=panel2, outline=line)

        draw.text((12, 48), "TRAINER SELF-TEST", font=self.font_mid, fill=text)

        draw.rounded_rectangle((216, 46, 306, 70), radius=8, fill=panel, outline=status_colour)
        draw.text((226, 51), status, font=self.font_small, fill=status_colour)

        if not result:
            draw.text((12, 84), "No self-test run yet.", font=self.font_mid, fill=muted)
            draw.text((12, 112), "Use web UI:", font=self.font_small, fill=muted)
            draw.text((12, 128), "Trainer > Generate + Decode", font=self.font_small, fill=text)
            self.draw_button_bar(draw, colours)
            return

        tone = result.get("tone_hz", cfg.get("cw_generator_tone_hz", cfg.get("target_tone_hz", "--")))
        wpm = result.get("wpm", cfg.get("cw_generator_wpm", cfg.get("initial_wpm", "--")))
        fwpm = result.get("farnsworth_wpm", cfg.get("cw_generator_farnsworth_wpm", wpm))
        conf = float(result.get("confidence") or 0.0)
        snr = float(result.get("snr_db") or 0.0)

        rows = [
            ("Tone", f"{tone} Hz"),
            ("Speed", f"{float(wpm):.2f} / {float(fwpm):.2f} WPM"),
            ("Conf", f"{conf:.2f}"),
            ("SNR", f"{snr:.1f} dB"),
        ]

        y = 78
        for k, v in rows:
            draw.text((12, y), k, font=self.font_small, fill=muted)
            draw.text((72, y), v, font=self.font_small, fill=text)
            y += 14

        expected = self.clip_to_width(draw, str(result.get("expected") or ""), self.font_small, self.width - 28)
        decoded = self.clip_to_width(draw, str(result.get("decoded") or ""), self.font_small, self.width - 28)

        draw.text((12, 142), "Expected", font=self.font_small, fill=muted)
        draw.text((12, 156), expected or "--", font=self.font_small, fill=text)

        draw.text((12, 176), "Decoded", font=self.font_small, fill=muted)
        draw.text((12, 190), decoded or "--", font=self.font_small, fill=status_colour if status in ("PASS", "CLOSE", "FAIL") else text)

        self.draw_button_bar(draw, colours)


    def draw_splash(self):
        bg = (4, 8, 14)
        panel = (10, 18, 30)
        panel2 = (14, 24, 40)
        line = (45, 100, 180)
        text = (235, 245, 255)
        muted = (145, 165, 185)
        blue = (90, 190, 255)
        cyan = (90, 255, 255)
        green = (80, 255, 170)
        yellow = (255, 220, 90)

        img = Image.new("RGB", (self.width, self.height), bg)
        draw = ImageDraw.Draw(img)

        # Main frame.
        draw.rounded_rectangle((8, 8, self.width - 8, self.height - 8), radius=14, fill=panel, outline=line)
        draw.rounded_rectangle((11, 11, self.width - 11, self.height - 11), radius=12, outline=(20, 55, 95))

        # Title.
        title = "THE MORSE"
        title2 = "WHISPERER"
        tw, _ = self.measure_text(draw, title, self.font_big)
        draw.text(((self.width - tw) // 2, 22), title, font=self.font_big, fill=text)
        tw2, _ = self.measure_text(draw, title2, self.font_big)
        draw.text(((self.width - tw2) // 2, 48), title2, font=self.font_big, fill=blue)

        # Stylised radio/fox/whisper icon panel.
        icon_x1, icon_y1, icon_x2, icon_y2 = 116, 78, 204, 144
        draw.rounded_rectangle((icon_x1, icon_y1, icon_x2, icon_y2), radius=12, fill=panel2, outline=blue)

        # Fox/radio head, intentionally simple for 320x240 framebuffer.
        cx, cy = 160, 111
        draw.polygon([(cx - 30, cy - 8), (cx - 14, cy - 32), (cx - 8, cy - 4)], fill=(210, 220, 235), outline=(80, 120, 170))
        draw.polygon([(cx + 30, cy - 8), (cx + 14, cy - 32), (cx + 8, cy - 4)], fill=(210, 220, 235), outline=(80, 120, 170))
        draw.polygon([(cx - 32, cy - 6), (cx, cy - 24), (cx + 32, cy - 6), (cx + 20, cy + 24), (cx, cy + 34), (cx - 20, cy + 24)], fill=(185, 195, 215), outline=(80, 120, 170))
        draw.polygon([(cx - 14, cy + 6), (cx, cy + 30), (cx + 14, cy + 6)], fill=(235, 240, 248))
        draw.ellipse((cx - 18, cy - 2, cx - 10, cy + 6), fill=(10, 18, 30))
        draw.ellipse((cx + 10, cy - 2, cx + 18, cy + 6), fill=(10, 18, 30))
        draw.ellipse((cx - 4, cy + 8, cx + 4, cy + 14), fill=(20, 28, 38))

        # CW/radio vibe.
        draw.text((26, 154), "CW DECODER APPLIANCE", font=self.font_small, fill=muted)
        draw.text((26, 170), "AUTO TONE  ·  LIVE COPY  ·  WEB UI", font=self.font_tiny, fill=blue)

        ip = local_ip()
        port = int(self.config.get("web_port", 8080))
        url = f"http://{ip}:{port}"
        url = self.clip_to_width(draw, url, self.font_small, self.width - 52)
        draw.text((26, 186), url, font=self.font_small, fill=green)

        # Loading/progress strip based on elapsed splash time.
        total = max(0.1, float(self.splash_seconds or 4.0))
        remaining = max(0.0, self.splash_until - time.time())
        progress = max(0.0, min(1.0, 1.0 - (remaining / total)))

        bar_x, bar_y, bar_w, bar_h = 26, 210, self.width - 52, 10
        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=5, fill=(6, 12, 20), outline=(50, 80, 110))
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=5, fill=blue)

        dot = "SEARCHING FOR CW..."
        dw, _ = self.measure_text(draw, dot, self.font_tiny)
        draw.text(((self.width - dw) // 2, 224), dot, font=self.font_tiny, fill=yellow)

        return img

    def draw_screen(self):
        if self.splash_enabled and time.time() < self.splash_until:
            return self.draw_splash()

        snap = self.state.snapshot()

        bg = (5, 9, 14)
        panel = (14, 22, 30)
        panel2 = (20, 31, 42)
        line = (45, 60, 75)
        text = (235, 245, 255)
        muted = (140, 155, 170)
        green = (60, 255, 140)
        blue = (90, 180, 255)
        yellow = (255, 210, 90)
        red = (255, 90, 90)
        colours = (bg, panel, panel2, line, text, muted, green, blue, yellow, red)

        img = Image.new("RGB", (self.width, self.height), bg)
        draw = ImageDraw.Draw(img)

        self.draw_header(draw, colours)

        if self.page == "STATUS":
            self.draw_status_page(draw, snap, colours)
        elif self.page == "RAW":
            self.draw_raw_page(draw, snap, colours)
        elif self.page == "SETTINGS":
            self.draw_settings_page(draw, snap, colours)
        elif self.page == "TRAINER":
            self.draw_trainer_page(draw, snap, colours)
        else:
            self.draw_copy_page(draw, snap, colours)

        return img

    def write_fb(self, img: Image.Image):
        if self.rotate:
            img = img.rotate(self.rotate, expand=True)
            img = img.resize((self.width, self.height))

        rgb = img.convert("RGB")

        # Software brightness fallback.
        #
        # The XC9022 / GoodTFT-style fb_ili9340 display does not expose
        # /sys/class/backlight on this build, so hardware dimming is unavailable.
        # Read the live config from SharedState each frame so web changes apply
        # without a service restart.
        try:
            live_cfg = {}
            try:
                snap = self.state.snapshot()
                live_cfg = snap.get("config", {}) if isinstance(snap, dict) else {}
            except Exception:
                live_cfg = {}

            percent = float(
                live_cfg.get(
                    "lcd_brightness_percent",
                    self.config.get("lcd_brightness_percent", 100),
                )
                or 100
            )

            # Clamp to visible-but-obvious software dimming.
            factor = max(0.05, min(1.0, percent / 100.0))

            if factor < 0.995:
                # point() is fast enough for this 320x240 framebuffer.
                rgb = rgb.point(lambda v: int(v * factor))
        except Exception:
            pass

        data = bytearray()
        for r, g, b in rgb.getdata():
            v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            data.append(v & 0xFF)
            data.append((v >> 8) & 0xFF)

        try:
            with open(self.fb_path, "wb", buffering=0) as fb:
                fb.write(data)
        except Exception as e:
            self.state.append_status(f"LCD write failed: {e}")

    def loop(self):
        while not self.stop_event.is_set():
            try:
                self.check_control_requests()
                img = self.frozen_img if self.frozen_img is not None else self.draw_screen()
                self.write_fb(img)
            except Exception as e:
                self.state.append_status(f"LCD draw failed: {e}")
            time.sleep(self.refresh)
