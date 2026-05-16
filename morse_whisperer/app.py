from __future__ import annotations

import signal
import threading
import time
from dataclasses import asdict

from .audio import AudioRing, start_capture
from .config import load_config
from .display import FramebufferDisplay
from .dsp import analyse_samples
from .state import SharedState
from .web import create_app


class MorseWhispererApp:
    def __init__(self) -> None:
        self.config = load_config()
        self.state = SharedState()
        self.state.merge(config=self.config)
        self.stop = threading.Event()
        self.ring = AudioRing(int(self.config["sample_rate"]), float(self.config.get("audio_queue_seconds", 60)))
        self.display = None
        self.decode_history = []

    def start(self) -> None:
        self.state.append_status("Audio capture started")
        start_capture(self.ring, str(self.config.get("audio_device", "plughw:2,0")), int(self.config["sample_rate"]), int(self.config.get("audio_blocksize", 64)), self.stop)
        if self.config.get("display_enabled", True):
            self.display = FramebufferDisplay(self.config, self.state)
            self.display.start()
        threading.Thread(target=self._decode_loop, name="decode-loop", daemon=True).start()
        flask = create_app(self.state, self.config)
        self.state.append_status(f"Web UI ready: http://0.0.0.0:{self.config.get('web_port',8080)}")
        flask.run(host=str(self.config.get("web_host", "0.0.0.0")), port=int(self.config.get("web_port", 8080)), threaded=True)

    def _decode_loop(self) -> None:
        while not self.stop.is_set():
            try:
                samples = self.ring.latest(float(self.config.get("decode_window_sec", 10)))
                result = analyse_samples(samples, self.config)
                d = asdict(result)
                accepted = bool(d.get("copy")) and result.confidence >= float(self.config.get("copy_min_confidence", 0.85))
                decode = {"accepted": accepted, "copy": d.get("copy", ""), "raw": d.get("raw", ""), "events": d.get("events", [])}
                if accepted:
                    item = {"ts": time.time(), "copy": decode["copy"], "raw": decode["raw"], "quality": {k: d.get(k) for k in ("selected_tone_hz", "snr_db", "confidence", "wpm", "dot_ms")}}
                    self.decode_history.append(item)
                    self.decode_history = self.decode_history[-25:]
                self.state.merge(quality=d, audio=d.get("audio", {}), decode=decode, decode_history=self.decode_history, audio_buffer={"buffered_seconds": self.ring.buffered_seconds(), "overruns": self.ring.overruns})
            except Exception as e:
                self.state.append_status(f"decode error: {e}")
            time.sleep(float(self.config.get("update_interval_sec", 1)))


def main() -> None:
    app = MorseWhispererApp()
    signal.signal(signal.SIGTERM, lambda *_: app.stop.set())
    app.start()
