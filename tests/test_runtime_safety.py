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

    def test_radio_preanalysis_gate_skips_only_near_silence(self) -> None:
        app = MorseWhispererApp()
        app.config.update({
            "radio_keyed_tone_scoring": True,
            "radio_search_min_rms": 0.0015,
            "radio_search_min_peak": 0.006,
        })

        quiet = np.full(8000, 0.0002, dtype=np.float32)
        weak = np.sin(2 * np.pi * 675 * np.arange(8000) / 8000.0).astype(np.float32) * 0.004

        self.assertFalse(app.should_analyse_recent(quiet)[0])
        self.assertTrue(app.should_analyse_recent(weak)[0])


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
            self.assertEqual(result["audio_device"], "plughw:9,0")


if __name__ == "__main__":
    unittest.main()
