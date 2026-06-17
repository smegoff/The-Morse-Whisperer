from __future__ import annotations

import json
import os
import select
import struct
import threading
import time
from pathlib import Path
from typing import Callable, Optional


EV_SYN = 0
EV_KEY = 1
EV_ABS = 3

ABS_X = 0
ABS_Y = 1
ABS_PRESSURE = 24
BTN_TOUCH = 330

EVENT_STRUCT = struct.Struct("llHHi")


class TouchscreenMonitor:
    """Read Linux input events from the resistive TFT touchscreen."""

    def __init__(
        self,
        config: dict,
        state,
        on_reset: Callable[[], None],
        on_tone_scan: Callable[[], None],
        on_next_page: Callable[[], None],
        on_clear: Callable[[], None],
    ) -> None:
        self.config = config
        self.state = state
        self.on_reset = on_reset
        self.on_tone_scan = on_tone_scan
        self.on_next_page = on_next_page
        self.on_clear = on_clear

        self.enabled = bool(config.get("touchscreen_enabled", True))
        self.device = str(config.get("touchscreen_device", "auto") or "auto")
        self.width = int(config.get("display_width", 320))
        self.height = int(config.get("display_height", 240))
        self.raw_x_min = int(config.get("touchscreen_raw_x_min", 0))
        self.raw_x_max = int(config.get("touchscreen_raw_x_max", 4095))
        self.raw_y_min = int(config.get("touchscreen_raw_y_min", 0))
        self.raw_y_max = int(config.get("touchscreen_raw_y_max", 4095))
        self.swap_xy = bool(config.get("touchscreen_swap_xy", False))
        self.invert_x = bool(config.get("touchscreen_invert_x", False))
        self.invert_y = bool(config.get("touchscreen_invert_y", False))
        self.footer_top = int(config.get("touchscreen_footer_top", 200))
        self.debounce_sec = float(config.get("touchscreen_debounce_sec", 0.35))

        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

        self._raw_x: Optional[int] = None
        self._raw_y: Optional[int] = None
        self._pressure = 0
        self._touching = False
        self._last_action_at = 0.0

    def start(self) -> None:
        if not self.enabled:
            return

        path = self.find_device()
        if not path:
            self.state.append_status("Touchscreen disabled: ADS7846 input device not found")
            return

        if not os.access(path, os.R_OK):
            self.state.append_status(f"Touchscreen disabled: cannot read {path}")
            return

        self.device = path
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.state.append_status(f"Touchscreen active: {path}")

    def find_device(self) -> Optional[str]:
        if self.device != "auto":
            return self.device if os.path.exists(self.device) else None

        for event in sorted(Path("/sys/class/input").glob("event*")):
            name_path = event / "device" / "name"
            try:
                name = name_path.read_text(encoding="utf-8", errors="ignore").strip().lower()
            except Exception:
                continue
            if "ads7846" in name or "touchscreen" in name:
                return f"/dev/input/{event.name}"
        return None

    def normalise_axis(self, value: int, raw_min: int, raw_max: int, size: int, invert: bool) -> int:
        lo = min(raw_min, raw_max)
        hi = max(raw_min, raw_max)
        if hi <= lo:
            return 0
        ratio = (max(lo, min(hi, value)) - lo) / float(hi - lo)
        if invert:
            ratio = 1.0 - ratio
        return max(0, min(size - 1, int(round(ratio * (size - 1)))))

    def map_point(self, raw_x: int, raw_y: int) -> tuple[int, int]:
        x = self.normalise_axis(raw_x, self.raw_x_min, self.raw_x_max, self.width, self.invert_x)
        y = self.normalise_axis(raw_y, self.raw_y_min, self.raw_y_max, self.height, self.invert_y)
        if self.swap_xy:
            x, y = (
                max(0, min(self.width - 1, int(round(y * (self.width - 1) / max(1, self.height - 1))))),
                max(0, min(self.height - 1, int(round(x * (self.height - 1) / max(1, self.width - 1))))),
            )
        return x, y

    def mark_button(self, button: str, label: str) -> None:
        try:
            Path("/run/morse-whisperer-button.json").write_text(
                json.dumps({"button": button, "label": label, "until": time.time() + 0.45}),
                encoding="utf-8",
            )
        except Exception:
            pass

    def handle_tap(self, raw_x: int, raw_y: int) -> None:
        now = time.time()
        if (now - self._last_action_at) < self.debounce_sec:
            return
        self._last_action_at = now

        x, y = self.map_point(raw_x, raw_y)
        if y < self.footer_top:
            self.state.append_status(f"Touch ignored: x={x} y={y}")
            return

        idx = max(0, min(3, int(x / max(1, self.width / 4))))
        actions = [
            ("1", "PAGE", self.on_next_page),
            ("2", "SCAN", self.on_tone_scan),
            ("3", "RESET", self.on_reset),
            ("4", "CLEAR", self.on_clear),
        ]

        button, label, callback = actions[idx]
        self.mark_button(button, label)
        self.state.append_status(f"Touch {label}: raw={raw_x},{raw_y} mapped={x},{y}")
        callback()

    def process_event(self, ev_type: int, code: int, value: int) -> None:
        if ev_type == EV_ABS:
            if code == ABS_X:
                self._raw_x = value
            elif code == ABS_Y:
                self._raw_y = value
            elif code == ABS_PRESSURE:
                self._pressure = value

        elif ev_type == EV_KEY and code == BTN_TOUCH:
            if value:
                self._touching = True
            else:
                if self._touching and self._raw_x is not None and self._raw_y is not None:
                    self.handle_tap(self._raw_x, self._raw_y)
                self._touching = False
                self._pressure = 0

        elif ev_type == EV_SYN:
            return

    def loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                with open(self.device, "rb", buffering=0) as dev:
                    while not self.stop_event.is_set():
                        readable, _, _ = select.select([dev], [], [], 0.5)
                        if not readable:
                            continue
                        data = dev.read(EVENT_STRUCT.size)
                        if len(data) != EVENT_STRUCT.size:
                            continue
                        _sec, _usec, ev_type, code, value = EVENT_STRUCT.unpack(data)
                        self.process_event(ev_type, code, value)
            except Exception as e:
                self.state.append_status(f"Touchscreen read failed: {e}")
                time.sleep(2.0)
