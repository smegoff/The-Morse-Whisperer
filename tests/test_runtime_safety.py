from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from morse_whisperer.app import MorseWhispererApp
from morse_whisperer.cq import channel_status, cq_config, receive_status
from morse_whisperer.display import FramebufferDisplay
from morse_whisperer.state import SharedState
from morse_whisperer.touch import TouchscreenMonitor
from morse_whisperer.web import create_app


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

    def test_settings_api_saves_auto_clear_timeout(self) -> None:
        class DummyState:
            def snapshot(self):
                return {}

            def update(self, **kwargs):
                pass

            def append_status(self, message):
                pass

        config = {"clear_after_silence_sec": 20.0}
        app = create_app(DummyState(), None, config)

        with mock.patch("morse_whisperer.web.save_config"):
            response = app.test_client().post(
                "/api/settings",
                json={"clear_after_silence_sec": 999},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(config["clear_after_silence_sec"], 600.0)

    def test_cq_channel_status_marks_clear_idle_audio(self) -> None:
        snap = {
            "audio": {"level_status": "IDLE", "rms": 0.001},
            "quality": {"squelch_open": False, "recent_activity": False, "snr_db": 0.0},
            "decode": {"stable_copy": ""},
        }

        status = channel_status(snap, cq_config({"station_callsign": "ZL1SXG"}))

        self.assertEqual(status["state"], "clear")

    def test_cq_channel_status_marks_busy_decoded_copy(self) -> None:
        snap = {
            "audio": {"level_status": "LOW", "rms": 0.001},
            "quality": {"squelch_open": False, "recent_activity": False, "snr_db": 0.0},
            "decode": {"stable_copy": "CQ CQ DE ZL2ABC K"},
        }

        status = channel_status(snap, cq_config({"station_callsign": "ZL1SXG"}))

        self.assertEqual(status["state"], "busy")
        self.assertIn("decoded copy", status["reason"])

    def test_cq_receive_status_reports_audible_non_cq_audio(self) -> None:
        snap = {
            "audio": {"level_status": "GOOD", "rms": 0.012, "peak": 0.04},
            "quality": {"squelch_open": False, "recent_activity": False, "snr_db": 2.0},
            "decode": {},
        }

        status = receive_status(snap)

        self.assertEqual(status["state"], "audible")
        self.assertTrue(status["audible"])
        self.assertEqual(status["heard_text"], "")

    def test_cq_receive_status_flags_low_modulation(self) -> None:
        snap = {
            "audio": {"level_status": "LOW", "rms": 0.0035, "peak": 0.018},
            "quality": {"squelch_open": True, "recent_activity": True, "snr_db": 2.0},
            "decode": {},
        }

        status = receive_status(snap)

        self.assertIn("low_modulation", status["impairments"])

    def test_cq_receive_status_flags_qrn_spikes(self) -> None:
        snap = {
            "audio": {"level_status": "LOW", "rms": 0.004, "peak": 0.08},
            "quality": {"squelch_open": False, "recent_activity": True, "snr_db": 2.0},
            "decode": {},
        }

        status = receive_status(snap)

        self.assertIn("possible_qrn", status["impairments"])

    def test_cq_receive_status_flags_qrm_competing_tones(self) -> None:
        snap = {
            "audio": {"level_status": "GOOD", "rms": 0.02, "peak": 0.08},
            "quality": {
                "squelch_open": True,
                "recent_activity": True,
                "snr_db": 8.0,
                "tone_ranking": [
                    {"tone_hz": 700, "score": 1.0},
                    {"tone_hz": 720, "score": 0.8},
                ],
            },
            "decode": {},
        }

        status = receive_status(snap)

        self.assertIn("possible_qrm", status["impairments"])
        self.assertGreaterEqual(status["competitor_ratio"], 0.65)

    def test_cq_receive_status_prefers_candidate_copy(self) -> None:
        snap = {
            "audio": {"level_status": "LOW", "rms": 0.001, "peak": 0.003},
            "quality": {"squelch_open": False, "recent_activity": True, "snr_db": 4.0},
            "decode": {"candidate_copy": "UR RST 579"},
        }

        status = receive_status(snap)

        self.assertEqual(status["state"], "candidate")
        self.assertEqual(status["heard_text"], "UR RST 579")

    def test_cq_settings_api_keeps_transmit_disabled(self) -> None:
        class DummyState:
            def snapshot(self):
                return {
                    "audio": {"level_status": "IDLE", "rms": 0.0},
                    "quality": {"squelch_open": False, "recent_activity": False},
                    "decode": {},
                }

            def update(self, **kwargs):
                pass

            def append_status(self, message):
                pass

        config = {"station_callsign": "ZL1SXG", "cq_allow_transmit": True}
        app = create_app(DummyState(), None, config)

        with mock.patch("morse_whisperer.cq.save_config"):
            response = app.test_client().post(
                "/api/cq/settings",
                json={"cq_enabled": True, "cq_callsign": "zl1sxg", "cq_cat_baud": 999999},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(config["cq_enabled"])
        self.assertEqual(config["cq_callsign"], "ZL1SXG")
        self.assertEqual(config["cq_cat_baud"], 115200)
        self.assertFalse(config["cq_allow_transmit"])

    def test_cq_plan_uses_openai_config_without_transmit(self) -> None:
        class DummyState:
            def snapshot(self):
                return {
                    "audio": {"level_status": "LOW", "rms": 0.001},
                    "quality": {"squelch_open": False, "recent_activity": False, "snr_db": 0.0},
                    "decode": {"stable_copy": "CQ CQ DE ZL2ABC K"},
                }

            def update(self, **kwargs):
                pass

            def append_status(self, message):
                pass

        config = {
            "station_callsign": "ZL1SXG",
            "cq_callsign": "ZL1SXG",
            "cq_ai_enabled": True,
            "cq_ai_provider": "openai",
            "cq_ai_model": "gpt-4.1-mini",
        }
        app = create_app(DummyState(), None, config)

        with (
            mock.patch(
                "morse_whisperer.cq.analyse_copy",
                return_value={
                    "ok": True,
                    "provider": "openai",
                    "detected_intent": "calling_cq",
                    "their_call": "ZL2ABC",
                    "warnings": [],
                },
            ) as analyse,
            mock.patch(
                "morse_whisperer.cq.suggest_reply",
                return_value={
                    "ok": True,
                    "provider": "openai",
                    "suggested_reply_text": "ZL2ABC DE ZL1SXG ZL1SXG KN",
                    "warnings": [],
                },
            ),
        ):
            response = app.test_client().post("/api/cq/plan", json={"mode": "auto"})

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertFalse(body["transmit_available"])
        self.assertEqual(body["receive"]["state"], "decoded")
        self.assertEqual(body["reply"]["provider"], "openai")
        self.assertEqual(analyse.call_args.args[1]["ai_provider"], "openai")
        self.assertEqual(analyse.call_args.args[1]["ai_model"], "gpt-4.1-mini")

    def test_web_apps_are_separate_pages(self) -> None:
        state = SharedState()
        state.update(
            audio={"level_status": "IDLE", "rms": 0.0},
            quality={"squelch_open": False, "recent_activity": False},
            decode={},
        )
        app = create_app(state, None, {"station_callsign": "ZL1SXG"})
        client = app.test_client()
        decoder_html = client.get("/").data.decode("utf-8")
        self.assertEqual(state.snapshot()["ui"]["active_app"], "morse")
        cq_html = client.get("/cq").data.decode("utf-8")
        self.assertEqual(state.snapshot()["ui"]["active_app"], "cq")

        self.assertIn('href="/cq"', decoder_html)
        self.assertNotIn('id="cqRagChewCard"', decoder_html)
        self.assertIn("CQ Rag Chew", cq_html)
        self.assertIn("planCqReply", cq_html)

    def test_tft_draws_cq_active_app_screen(self) -> None:
        state = SharedState()
        state.update(
            ui={"active_app": "cq"},
            config={
                "cq_callsign": "ZL1SXG",
                "cq_cat_enabled": False,
                "cq_ai_provider": "openai",
                "cq_ai_model": "gpt-4.1-mini",
                "cq_busy_rms_threshold": 0.006,
                "cq_busy_snr_threshold_db": 6.0,
            },
            audio={"level_status": "IDLE", "rms": 0.0},
            quality={"squelch_open": False, "recent_activity": False, "snr_db": 0.0},
            decode={},
        )
        display = FramebufferDisplay({"display_enabled": False}, state)

        image = display.draw_screen()

        self.assertEqual(image.size, (display.width, display.height))


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
