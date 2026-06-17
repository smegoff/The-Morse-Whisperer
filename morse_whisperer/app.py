from __future__ import annotations

import socket
import threading
import time
import traceback
from dataclasses import asdict
from typing import Dict, List, Optional

import numpy as np

from .audio import AudioRing, start_capture
from .config import load_config
from .display import FramebufferDisplay
from .dsp import DecodeResult, analyse_samples, audio_metrics
from .state import SharedState
from .web import create_app
from .buttons import SafeTwoButtonMonitor
from .touch import TouchscreenMonitor


DYNAMIC_TONE_MODES = {"session_auto", "auto_session", "dynamic", "auto_lock"}


class MorseWhispererApp:
    def __init__(self, config_path: str | None = None) -> None:
        self.config = load_config(config_path) if config_path else load_config()
        self.state = SharedState()
        self.state.merge("config", self.config)

        self.sample_rate = int(self.config["sample_rate"])
        self.ring = AudioRing(
            self.sample_rate,
            float(self.config.get("audio_queue_seconds", 20)),
        )
        self.capture = None
        self.stop_event = threading.Event()

        self.last_good_copy = ""
        self.last_good_raw = ""
        self.last_good_at = 0.0

        self.session_chunks: List[np.ndarray] = []
        self.session_samples = 0
        self.last_total_samples: Optional[int] = None
        self.last_activity_at = 0.0
        self.session_started_at = 0.0

        self.squelch_open = False
        self.session_tone_hz: Optional[int] = None
        self.session_tone_reason = "none"
        self.pending_tone_hz: Optional[int] = None
        self.pending_tone_count = 0

        self.last_candidate_copy = ""
        self.last_candidate_raw = ""
        self.last_good_events = []
        self.last_good_quality = {}

        # Rolling history of accepted decodes for review/testing.
        # Kept small so /api/snapshot stays lightweight.
        self.decode_history = []

        self.display = None
        self.buttons = None
        self.touch = None

        # Updated by /api/reset in the web UI. The decoder loop watches this
        # so a reset clears internal stable copy/session state, not just HTML.
        self.last_reset_requested_at = 0.0

        # Updated by /api/tone/scan or Button 2. The decoder loop watches this
        # and forces the next live session to reacquire tone from current audio.
        self.last_tone_scan_requested_at = 0.0

    @staticmethod
    def local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def tone_mode(self) -> str:
        return str(self.config.get("tone_mode", "fixed")).lower()

    def dynamic_tone_enabled(self) -> bool:
        return self.tone_mode() in DYNAMIC_TONE_MODES

    def detect_config(self) -> Dict:
        cfg = dict(self.config)
        if self.dynamic_tone_enabled():
            cfg["tone_mode"] = "auto"
        return cfg

    def session_config(self) -> Dict:
        cfg = dict(self.config)
        if self.dynamic_tone_enabled():
            if self.session_tone_hz:
                cfg["tone_mode"] = "fixed"
                cfg["target_tone_hz"] = int(self.session_tone_hz)
            else:
                cfg["tone_mode"] = "auto"
        return cfg

    def request_restart_service(self) -> None:
        self.state.append_status("Restarting morse-whisperer service")
        try:
            import subprocess
            subprocess.Popen(
                ["/bin/systemctl", "restart", "morse-whisperer"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            self.state.append_status(f"Service restart failed: {e}")

    def next_display_page(self) -> None:
        if getattr(self, "display", None) is not None:
            self.display.next_page()
        else:
            self.state.append_status("TFT page requested but display is not active")

    def request_tone_scan(self) -> None:
        now = time.time()
        snap = self.state.snapshot()
        control = snap.get("control", {})
        if not isinstance(control, dict):
            control = {}
        control["tone_scan_requested_at"] = now
        control["tone_scan_counter"] = int(control.get("tone_scan_counter", 0)) + 1

        q = snap.get("quality", {})
        if not isinstance(q, dict):
            q = {}
        q.update({
            "live_tone_lock_hz": None,
            "live_tone_lock_reason": "manual_scan_requested",
            "reason": "manual_tone_scan_requested",
        })

        self.state.update(control=control, quality=q)
        self.state.append_status("Manual tone scan requested from TFT touch")

    def request_full_reset(self) -> None:
        self.clear_live_session(clear_tone=True)
        self.clear_accepted_copy()
        self.last_candidate_copy = ""
        self.last_candidate_raw = ""

        self.last_total_samples = None
        self.ring.clear()

        dec = {
            "raw": "",
            "copy": "",
            "stable_copy": "",
            "stable_raw": "",
            "candidate_raw": "",
            "candidate_copy": "",
            "events": [],
            "accepted": False,
            "live_mode": "button_reset",
        }

        q = self.result_quality_dict(None)
        q["reason"] = "button_reset"
        q["recent_activity"] = False
        q["quiet_for_sec"] = 0.0

        self.state.update(mode="running", decode=dec, quality=q, decode_history=list(self.decode_history))
        self.state.append_status("Decoder reset: copy/session/buffer cleared")

    def toggle_display_freeze(self) -> None:
        if getattr(self, "display", None) is not None:
            self.display.toggle_freeze()
        else:
            self.state.append_status("TFT freeze requested but display is not active")

    def start(self) -> None:
        self.state.update(mode="starting")
        self.capture = start_capture(self.ring, self.config)
        ai = asdict(self.capture.info())
        self.state.merge("audio", ai)
        self.state.append_status(f"Audio capture started: {ai}")

        decoder_thread = threading.Thread(target=self.decode_loop, daemon=True)
        decoder_thread.start()

        self.display = FramebufferDisplay(self.config, self.state)
        self.display.start()

        self.buttons = SafeTwoButtonMonitor(
            self.config,
            self.state,
            on_reset=self.request_full_reset,
            on_restart=self.request_restart_service,
            on_next_page=self.next_display_page,
            on_toggle_freeze=self.toggle_display_freeze,
        )
        self.buttons.start()

        self.touch = TouchscreenMonitor(
            self.config,
            self.state,
            on_reset=self.request_full_reset,
            on_tone_scan=self.request_tone_scan,
            on_next_page=self.next_display_page,
            on_clear=self.request_full_reset,
        )
        self.touch.start()

        app = create_app(self.state, self.ring, self.config)
        host = str(self.config.get("web_host", "0.0.0.0"))
        port = int(self.config.get("web_port", 8080))

        self.state.update(mode="running")
        self.state.append_status(f"Web UI ready: http://{self.local_ip()}:{port}")
        app.run(host=host, port=port, threaded=True, use_reloader=False)

    def clear_live_session(self, clear_tone: bool = True) -> None:
        self.session_chunks.clear()
        self.session_samples = 0
        self.last_activity_at = 0.0
        self.session_started_at = 0.0
        self.squelch_open = False
        if clear_tone:
            self.session_tone_hz = None
            self.session_tone_reason = "none"
            self.pending_tone_hz = None
            self.pending_tone_count = 0

    def add_decode_history(self, result: DecodeResult, events) -> None:
        try:
            max_items = int(self.config.get("decode_history_max", 10))
        except Exception:
            max_items = 10

        if max_items <= 0:
            return

        item = {
            "ts": time.time(),
            "copy": result.copy,
            "raw": result.raw,
            "tone_hz": result.selected_tone_hz,
            "target_tone_hz": result.target_tone_hz,
            "tone_mode": result.tone_mode,
            "dot_ms": result.dot_ms,
            "wpm": result.wpm,
            "snr_db": result.snr_db,
            "winner_ratio": result.winner_ratio,
            "confidence": result.confidence,
            "marks": result.marks,
            "spaces": result.spaces,
            "decoded_symbols": result.decoded_symbols,
            "failed_symbols": result.failed_symbols,
            "reason": result.reason,
            "event_count": len(events or []),
            "events": list(events or []),
        }

        # Avoid adding the exact same accepted copy repeatedly on every loop.
        if self.decode_history:
            last = self.decode_history[-1]
            if (
                last.get("copy") == item["copy"]
                and last.get("raw") == item["raw"]
                and abs(float(item["ts"]) - float(last.get("ts") or 0)) < 8.0
            ):
                self.decode_history[-1] = item
            else:
                self.decode_history.append(item)
        else:
            self.decode_history.append(item)

        self.decode_history = self.decode_history[-max_items:]
        self.state.update(decode_history=list(self.decode_history))

    def clear_accepted_copy(self) -> None:
        self.last_good_copy = ""
        self.last_good_raw = ""
        self.last_good_at = 0.0
        self.last_good_events = []
        self.last_good_quality = {}

    def lock_session_tone(self, result: DecodeResult | None) -> None:
        fallback = int(self.config.get("target_tone_hz", 700))

        if not self.dynamic_tone_enabled():
            self.session_tone_hz = fallback
            self.session_tone_reason = "fixed"
            return

        if result is None:
            self.session_tone_hz = fallback
            self.session_tone_reason = "fallback_no_result"
            return

        min_ratio = float(self.config.get("session_auto_min_ratio", 4.0))
        min_snr = float(self.config.get("session_auto_min_snr", 8.0))

        if result.winner_ratio >= min_ratio and result.snr_db >= min_snr:
            self.session_tone_hz = int(result.selected_tone_hz)
            self.session_tone_reason = f"auto ratio={result.winner_ratio:.1f} snr={result.snr_db:.1f}"
        else:
            self.session_tone_hz = fallback
            self.session_tone_reason = f"fallback weak tone ratio={result.winner_ratio:.1f} snr={result.snr_db:.1f}"

    def consider_session_relock(self, result: DecodeResult | None) -> None:
        if not result or not self.dynamic_tone_enabled() or not self.session_tone_hz:
            return

        candidate = int(result.selected_tone_hz)
        tolerance = int(self.config.get("session_relock_tolerance_hz", 20))
        if abs(candidate - int(self.session_tone_hz)) <= tolerance:
            self.pending_tone_hz = None
            self.pending_tone_count = 0
            return

        min_ratio = float(self.config.get("session_relock_min_ratio", 2.0))
        min_snr = float(self.config.get("session_relock_min_snr", 7.0))
        min_contrast = float(self.config.get("session_relock_min_contrast", 0.35))
        if (
            result.winner_ratio < min_ratio
            or result.snr_db < min_snr
            or result.envelope_contrast < min_contrast
        ):
            self.pending_tone_hz = None
            self.pending_tone_count = 0
            return

        if self.pending_tone_hz is not None and abs(candidate - self.pending_tone_hz) <= tolerance:
            self.pending_tone_count += 1
        else:
            self.pending_tone_hz = candidate
            self.pending_tone_count = 1

        required = max(2, int(self.config.get("session_relock_confirmations", 3)))
        if self.pending_tone_count >= required:
            old = self.session_tone_hz
            self.session_tone_hz = candidate
            self.session_tone_reason = f"relocked {old}->{candidate} Hz"
            self.pending_tone_hz = None
            self.pending_tone_count = 0
            self.state.append_status(f"Radio tone relocked: {old} Hz -> {candidate} Hz")

    def append_live_session(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return

        if not self.session_chunks:
            self.session_started_at = time.time()

        data = samples.astype(np.float32, copy=True)
        self.session_chunks.append(data)
        self.session_samples += int(data.size)

        max_sec = float(self.config.get("live_session_max_sec", 45.0))
        max_samples = int(self.sample_rate * max_sec)

        while self.session_samples > max_samples and self.session_chunks:
            extra = self.session_samples - max_samples
            first = self.session_chunks[0]
            if first.size <= extra:
                self.session_samples -= int(first.size)
                self.session_chunks.pop(0)
            else:
                self.session_chunks[0] = first[extra:]
                self.session_samples -= int(extra)
                break

    def live_session_array(self) -> np.ndarray:
        if not self.session_chunks:
            return np.zeros(0, dtype=np.float32)
        if len(self.session_chunks) == 1:
            return self.session_chunks[0]
        return np.concatenate(self.session_chunks).astype(np.float32, copy=False)

    def get_new_samples(self, stats: Dict[str, float | int]) -> np.ndarray:
        total = int(stats.get("total_samples", 0))
        buffered = int(stats.get("buffered_samples", 0))

        if buffered == 0:
            self.clear_live_session()
            self.clear_accepted_copy()
            self.last_total_samples = total
            return np.zeros(0, dtype=np.float32)

        if self.last_total_samples is None:
            new_count = min(
                buffered,
                int(self.sample_rate * float(self.config.get("update_interval_sec", 2.0))),
            )
        else:
            new_count = max(0, total - self.last_total_samples)

        self.last_total_samples = total

        if new_count <= 0:
            return np.zeros(0, dtype=np.float32)

        seconds = max(
            0.25,
            min(
                float(self.config.get("audio_queue_seconds", 20)),
                (new_count / float(self.sample_rate)) + 0.25,
            ),
        )

        recent = self.ring.last(seconds)
        if recent.size == 0:
            return recent

        return recent[-min(new_count, recent.size):].astype(np.float32, copy=False)

    def is_recent_activity(self, recent_result: DecodeResult) -> bool:
        min_snr = float(self.config.get("live_active_snr", 10.0))
        min_marks = int(self.config.get("live_active_min_marks", 2))
        min_rms = float(self.config.get("live_active_min_rms", 0.012))
        min_peak = float(self.config.get("live_active_min_peak", 0.050))

        audio = recent_result.audio or {}
        rms = float(audio.get("rms", 0.0))
        peak = float(audio.get("peak", 0.0))
        level = str(audio.get("level_status", ""))

        if recent_result.reason not in ("ok", "target_tone_mismatch"):
            return False
        relative_activity = bool(self.config.get("radio_relative_activity", False))
        min_contrast = float(self.config.get("radio_activity_min_contrast", 0.30))
        if relative_activity:
            if recent_result.envelope_contrast < min_contrast:
                return False
        else:
            if level in ("IDLE", "LOW"):
                return False
            if rms < min_rms:
                return False
            if peak < min_peak:
                return False
        if recent_result.snr_db < min_snr:
            return False
        if recent_result.marks < min_marks:
            return False
        return True

    def should_analyse_recent(self, samples: np.ndarray) -> tuple[bool, Dict]:
        metrics = asdict(audio_metrics(samples))
        if not bool(self.config.get("radio_keyed_tone_scoring", False)):
            return True, metrics

        min_rms = float(self.config.get("radio_search_min_rms", 0.0015))
        min_peak = float(self.config.get("radio_search_min_peak", 0.006))
        should_analyse = (
            float(metrics.get("rms", 0.0)) >= min_rms
            or float(metrics.get("peak", 0.0)) >= min_peak
        )
        return should_analyse, metrics

    def is_publishable(self, result: DecodeResult) -> bool:
        min_conf = float(self.config.get("copy_min_confidence", 0.85))
        min_snr = float(self.config.get("copy_min_snr", self.config.get("squelch_snr", 3.5)))
        min_symbols = int(self.config.get("copy_min_decoded_symbols", 5))
        max_failed = int(self.config.get("copy_max_failed_symbols", 0))

        if not result.copy:
            return False
        if result.reason not in ("ok", "target_tone_mismatch"):
            return False
        if result.target_detected_mismatch and not self.dynamic_tone_enabled():
            return False
        if result.confidence < min_conf:
            return False
        if result.snr_db < min_snr:
            return False
        if result.decoded_symbols < min_symbols:
            return False
        if result.failed_symbols > max_failed:
            return False
        if "#" in result.copy and max_failed == 0:
            return False
        return True

    def should_replace_copy(self, candidate: str) -> bool:
        candidate = (candidate or "").strip()
        old = (self.last_good_copy or "").strip()

        if not candidate:
            return False
        if not old:
            return True
        if candidate == old:
            return True
        if old in candidate:
            return True
        if candidate.startswith(old[:max(3, min(len(old), 8))]) and len(candidate) >= len(old):
            return True
        if len(candidate) >= len(old) + 3:
            return True

        return False

    def result_quality_dict(self, result: DecodeResult | None) -> Dict:
        base = {
            "live_mode": "session_auto_tone" if self.dynamic_tone_enabled() else "session_fixed_tone",
            "squelch_open": self.squelch_open,
            "live_tone_lock_hz": self.session_tone_hz,
            "live_tone_lock_reason": self.session_tone_reason,
            "live_session_seconds": self.session_samples / float(self.sample_rate),
            "live_session_samples": self.session_samples,
        }

        if result is None:
            base.update({"reason": "waiting_for_audio"})
            return base

        base.update({
            "selected_tone_hz": result.selected_tone_hz,
            "target_tone_hz": result.target_tone_hz,
            "tone_mode": result.tone_mode,
            "target_detected_mismatch": result.target_detected_mismatch,
            "winner_ratio": result.winner_ratio,
            "snr_db": result.snr_db,
            "confidence": result.confidence,
            "dot_ms": result.dot_ms,
            "wpm": result.wpm,
            "threshold": result.threshold,
            "low_threshold": result.low_threshold,
            "high_threshold": result.high_threshold,
            "tone_ranking": result.tone_ranking,
            "marks": result.marks,
            "spaces": result.spaces,
                "events": result.events,
            "decoded_symbols": result.decoded_symbols,
            "failed_symbols": result.failed_symbols,
            "envelope_contrast": result.envelope_contrast,
            "envelope_transitions": result.envelope_transitions,
            "reason": result.reason,
        })
        return base

    def update_state_blank_or_stable(self, audio: Dict, quality: Dict, candidate: DecodeResult | None = None) -> None:
        show_candidates = bool(self.config.get("show_rejected_candidates", False))

        dec = {
            "raw": self.last_good_raw,
            "copy": self.last_good_copy,
            "stable_copy": self.last_good_copy,
            "stable_raw": self.last_good_raw,
            "candidate_raw": candidate.raw if show_candidates and candidate is not None else "",
            "candidate_copy": candidate.copy if show_candidates and candidate is not None else "",
            "events": list(getattr(self, "last_good_events", [])),
            "accepted_events": list(getattr(self, "last_good_events", [])),
            "stable_quality": dict(getattr(self, "last_good_quality", {})),
            "accepted": False,
            "live_mode": quality.get("live_mode", ""),
        }
        self.state.update(mode="running", decode=dec, quality=quality, audio=audio, decode_history=list(self.decode_history))

    def check_external_tone_scan(self) -> None:
        snap = self.state.snapshot()
        control = snap.get("control", {}) if isinstance(snap, dict) else {}

        try:
            requested_at = float(control.get("tone_scan_requested_at") or 0.0)
        except Exception:
            requested_at = 0.0

        if not requested_at or requested_at <= self.last_tone_scan_requested_at:
            return

        self.last_tone_scan_requested_at = requested_at

        # Force a fresh tone acquisition from current live audio.
        # Do not clear accepted COPY unless the operator explicitly presses
        # reset. Manual scan should retune, not nuke useful copy.
        self.clear_live_session(clear_tone=True)
        self.session_tone_hz = None
        self.session_tone_reason = "manual_scan_pending"
        self.last_total_samples = None

        # Drop old buffered audio so stale tone/noise does not poison the scan.
        self.ring.clear()

        snap = self.state.snapshot()
        q = snap.get("quality", {})
        if not isinstance(q, dict):
            q = {}

        q.update({
            "live_tone_lock_hz": None,
            "live_tone_lock_reason": "manual_scan_pending",
            "reason": "manual_tone_scan_pending",
            "recent_activity": False,
            "live_session_seconds": 0,
            "live_session_samples": 0,
        })

        self.state.update(mode="running", quality=q)
        self.state.append_status("Manual tone scan acknowledged by decoder loop")

    def check_external_reset(self) -> None:
        snap = self.state.snapshot()
        control = snap.get("control", {}) if isinstance(snap, dict) else {}
        try:
            requested_at = float(control.get("reset_requested_at") or 0.0)
        except Exception:
            requested_at = 0.0

        if not requested_at or requested_at <= self.last_reset_requested_at:
            return

        self.last_reset_requested_at = requested_at

        # Clear all decoder-side memory. This is the bit the old web reset
        # missed, which let previous copy reappear after one refresh.
        self.clear_live_session(clear_tone=True)
        self.clear_accepted_copy()
        self.last_candidate_copy = ""
        self.last_candidate_raw = ""

        self.last_total_samples = None

        # Clear the audio ring again from the decoder side as well.
        self.ring.clear()

        dec = {
            "raw": "",
            "copy": "",
            "stable_copy": "",
            "stable_raw": "",
            "candidate_raw": "",
            "candidate_copy": "",
            "events": [],
            "accepted": False,
            "live_mode": "reset",
        }

        q = self.result_quality_dict(None)
        q["reason"] = "reset"
        q["recent_activity"] = False
        q["quiet_for_sec"] = 0.0

        self.state.update(mode="running", decode=dec, quality=q, decode_history=list(self.decode_history))
        self.state.append_status("Reset acknowledged by decoder loop")

    def decode_loop(self) -> None:
        update = float(self.config.get("update_interval_sec", 2.0))
        end_silence = float(self.config.get("live_end_silence_sec", 2.5))
        clear_silence = float(self.config.get("clear_after_silence_sec", 18.0))

        while not self.stop_event.is_set():
            try:
                self.check_external_reset()
                self.check_external_tone_scan()
                stats = self.ring.stats()
                new_samples = self.get_new_samples(stats)

                audio = dict(stats)
                if self.capture:
                    audio.update(asdict(self.capture.info()))

                recent_result = None
                activity = False

                if new_samples.size >= int(self.sample_rate * 0.25):
                    should_analyse, preliminary_audio = self.should_analyse_recent(new_samples)
                    preliminary_audio.update(audio)
                    audio = preliminary_audio
                    if should_analyse:
                        recent_result = analyse_samples(new_samples, self.detect_config())
                        recent_audio = dict(recent_result.audio)
                        recent_audio.update(audio)
                        audio = recent_audio
                        activity = self.is_recent_activity(recent_result)

                now = time.time()

                if bool(self.config.get("live_noise_gate_enabled", True)):
                    if activity:
                        if not self.squelch_open:
                            self.clear_live_session(clear_tone=True)
                            self.squelch_open = True
                            self.session_started_at = now
                            self.lock_session_tone(recent_result)
                        elif self.session_tone_hz is None:
                            self.lock_session_tone(recent_result)
                        else:
                            self.consider_session_relock(recent_result)

                        self.last_activity_at = now
                        self.append_live_session(new_samples)

                    else:
                        if self.squelch_open and self.last_activity_at and (now - self.last_activity_at) < end_silence:
                            if new_samples.size:
                                self.append_live_session(new_samples)
                        elif self.squelch_open:
                            self.clear_live_session(clear_tone=True)
                else:
                    if new_samples.size:
                        self.append_live_session(new_samples)
                    if activity:
                        self.last_activity_at = now
                        self.squelch_open = True
                        if self.session_tone_hz is None:
                            self.lock_session_tone(recent_result)

                if (
                    self.last_good_at
                    and (now - self.last_good_at) > clear_silence
                    and not self.squelch_open
                    and audio.get("level_status") in ("IDLE", "LOW")
                ):
                    self.clear_accepted_copy()

                session = self.live_session_array()

                if session.size < int(self.sample_rate * 0.5):
                    q = self.result_quality_dict(recent_result)
                    q["recent_activity"] = activity
                    q["quiet_for_sec"] = now - self.last_activity_at if self.last_activity_at else 0.0
                    self.update_state_blank_or_stable(audio, q, recent_result)
                    time.sleep(update)
                    continue

                result = analyse_samples(session, self.session_config())
                accepted = self.is_publishable(result)

                self.last_candidate_copy = result.copy
                self.last_candidate_raw = result.raw

                max_events = int(self.config.get("max_events_in_snapshot", 80))
                events = result.events[-max_events:] if max_events > 0 else []

                if accepted and self.should_replace_copy(result.copy):
                    self.last_good_copy = result.copy
                    self.last_good_raw = result.raw
                    self.last_good_at = now
                    self.last_good_events = list(events)
                    self.add_decode_history(result, events)
                    self.last_good_quality = {
                        "dot_ms": result.dot_ms,
                        "wpm": result.wpm,
                        "selected_tone_hz": result.selected_tone_hz,
                        "target_tone_hz": result.target_tone_hz,
                        "tone_mode": result.tone_mode,
                        "winner_ratio": result.winner_ratio,
                        "snr_db": result.snr_db,
                        "confidence": result.confidence,
                        "marks": result.marks,
                        "spaces": result.spaces,
                        "decoded_symbols": result.decoded_symbols,
                        "failed_symbols": result.failed_symbols,
                        "reason": result.reason,
                    }

                q = self.result_quality_dict(result)
                q["recent_activity"] = activity
                q["quiet_for_sec"] = now - self.last_activity_at if self.last_activity_at else 0.0

                show_candidates = bool(self.config.get("show_rejected_candidates", False))

                dec = {
                    "raw": self.last_good_raw,
                    "copy": self.last_good_copy,
                    "stable_copy": self.last_good_copy,
                    "stable_raw": self.last_good_raw,
                    "candidate_raw": result.raw if show_candidates else "",
                    "candidate_copy": result.copy if show_candidates else "",
                    "events": events if accepted else list(getattr(self, "last_good_events", [])),
                    "accepted_events": list(getattr(self, "last_good_events", [])),
                    "stable_quality": dict(getattr(self, "last_good_quality", {})),
                    "accepted": accepted,
                    "live_mode": q.get("live_mode", ""),
                }

                self.state.update(mode="running", decode=dec, quality=q, audio=audio, decode_history=list(self.decode_history))

            except Exception as e:
                self.state.append_status(f"Decode loop error: {e}")
                self.state.append_status(traceback.format_exc().splitlines()[-1])

            time.sleep(update)


def main() -> None:
    MorseWhispererApp().start()


if __name__ == "__main__":
    main()
