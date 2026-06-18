from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from morse_whisperer.app import MorseWhispererApp
from morse_whisperer.display import FramebufferDisplay
from morse_whisperer.touch import TouchscreenMonitor


class RuntimeResetTests(unittest.TestCase):
    def test_reset_keeps_controller_references(self) -> None:
        app = MorseWhispererApp()
        display = object()
        buttons = object()
        app.display = display
        app.buttons = buttons

        app.request_full_reset()

        self.assertIs(app.display, display)
        self.assertIs(app.buttons, buttons)

    def test_radio_preanalysis_gate_can_be_disabled_for_weak_inputs(self) -> None:
        app = MorseWhispererApp()
        app.config.update({
            "radio_keyed_tone_scoring": True,
            "radio_search_min_rms": 0.0,
            "radio_search_min_peak": 0.0,
        })

        disconnected = np.zeros(8000, dtype=np.float32)
        weak_receiver_audio = np.full(8000, 0.0002, dtype=np.float32)

        self.assertTrue(app.should_analyse_recent(disconnected)[0])
        self.assertTrue(app.should_analyse_recent(weak_receiver_audio)[0])

    def test_touchscreen_footer_mapping(self) -> None:
        actions = []

        class DummyState:
            def append_status(self, message):
                pass

        monitor = TouchscreenMonitor(
            {
                "display_width": 320,
                "display_height": 240,
                "touchscreen_footer_top": 200,
            },
            DummyState(),
            on_reset=lambda: actions.append("reset"),
            on_tone_scan=lambda: actions.append("scan"),
            on_next_page=lambda: actions.append("page"),
            on_clear=lambda: actions.append("clear"),
        )

        for raw_x in (100, 1500, 2600, 3900):
            monitor._last_action_at = 0
            monitor.handle_tap(raw_x, 3900)

        self.assertEqual(actions, ["page", "scan", "reset", "clear"])

    def test_tft_sleep_uses_idle_timeout(self) -> None:
        class DummyState:
            def __init__(self):
                self.snap = {
                    "config": {
                        "tft_screen_timeout_enabled": True,
                        "tft_screen_timeout_sec": 15,
                    },
                    "quality": {"recent_activity": False, "squelch_open": False},
                    "audio": {"level_status": "IDLE"},
                    "decode": {"accepted": False},
                }

            def snapshot(self):
                return self.snap

            def append_status(self, message):
                pass

        display = FramebufferDisplay({"display_enabled": False}, DummyState())
        display.last_screen_activity_at -= 16
        self.assertTrue(display.should_sleep(display.state.snapshot()))

        display.state.snap["quality"]["recent_activity"] = True
        self.assertFalse(display.should_sleep(display.state.snapshot()))


class ProfileSwitchTests(unittest.TestCase):
    def test_switch_preserves_non_profile_settings(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        helper = repo / "tools" / "set_decoder_profile.py"

        with tempfile.TemporaryDirectory() as tmp_dir:
            app_dir = Path(tmp_dir)
            (app_dir / "profiles").mkdir()
            (app_dir / "profiles" / "kiwi.json").write_text(
                json.dumps(
                    {
                        "target_tone_hz": 650,
                        "threshold_bias": 0.5,
                        "decoder_profile": "kiwi",
                        "decoder_profile_name": "Radio CW",
                    }
                ),
                encoding="utf-8",
            )
            (app_dir / "config.json").write_text(
                json.dumps(
                    {
                        "target_tone_hz": 700,
                        "threshold_bias": 0.48,
                        "audio_device": "plughw:9,0",
                        "station_callsign": "TEST1",
                        "input_capture_percent": 17,
                        "decoder_profile": "clean",
                    }
                ),
                encoding="utf-8",
            )

            env = dict(os.environ)
            env["MW_APP_DIR"] = str(app_dir)
            subprocess.run([sys.executable, str(helper), "kiwi"], check=True, env=env)

            result = json.loads((app_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(result["target_tone_hz"], 650)
            self.assertEqual(result["decoder_profile"], "kiwi")
            self.assertEqual(result["audio_device"], "plughw:9,0")
            self.assertEqual(result["station_callsign"], "TEST1")
            self.assertEqual(result["input_capture_percent"], 17)
            self.assertFalse((app_dir / "config.json.tmp").exists())

    def test_clean_switch_removes_radio_only_keys(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        helper = repo / "tools" / "set_decoder_profile.py"

        with tempfile.TemporaryDirectory() as tmp_dir:
            app_dir = Path(tmp_dir)
            (app_dir / "profiles").mkdir()
            (app_dir / "profiles" / "clean.json").write_text(
                json.dumps(
                    {
                        "target_tone_hz": 700,
                        "decoder_profile": "clean",
                        "decoder_profile_name": "Clean CW",
                    }
                ),
                encoding="utf-8",
            )
            (app_dir / "config.json").write_text(
                json.dumps(
                    {
                        "target_tone_hz": 650,
                        "decoder_profile": "kiwi",
                        "radio_keyed_tone_scoring": True,
                        "radio_fine_tone_search": True,
                        "radio_qrn_blanker_enabled": True,
                        "radio_event_cleanup_enabled": True,
                        "audio_device": "plughw:9,0",
                    }
                ),
                encoding="utf-8",
            )

            env = dict(os.environ)
            env["MW_APP_DIR"] = str(app_dir)
            subprocess.run([sys.executable, str(helper), "clean"], check=True, env=env)

            result = json.loads((app_dir / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(result["decoder_profile"], "clean")
            self.assertNotIn("radio_keyed_tone_scoring", result)
            self.assertNotIn("radio_fine_tone_search", result)
            self.assertNotIn("radio_qrn_blanker_enabled", result)
            self.assertNotIn("radio_event_cleanup_enabled", result)
            self.assertEqual(result["audio_device"], "plughw:9,0")


if __name__ == "__main__":
    unittest.main()
