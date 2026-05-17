from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = os.environ.get("MW_CONFIG", "/opt/morse-whisperer-pi/config.json")

DEFAULTS: Dict[str, Any] = {
    "sample_rate": 8000,
    "target_tone_hz": 700,
    "tone_mode": "session_auto",
    "allowed_tones_hz": [400,500,550,600,650,700,750,800,850,900,950,1000],
    "initial_wpm": 18.75,
    "threshold_bias": 0.48,
    "window_ms": 12,
    "hop_ms": 8,
    "decode_window_sec": 10,
    "update_interval_sec": 1,
    "squelch_snr": 3.5,
    "audio_filter_enabled": True,
    "audio_filter_mode": "wide",
    "audio_filter_wide_hz": 500,
    "audio_filter_narrow_hz": 220,
    "audio_filter_bandwidth_hz": 300,
    "audio_filter_max_hz": 1200,
    "web_host": "0.0.0.0",
    "web_port": 8080,
    "display_enabled": True,
    "display_width": 320,
    "display_height": 240,
    "display_refresh_sec": 1.0,
    "framebuffer_candidates": ["/dev/fb1", "/dev/fb0"],
    "station_callsign": "N0CALL",
    "audio_device": "plughw:2,0",
    "audio_output_device": "plughw:2,0",
    "audio_backend": "arecord",
    "audio_blocksize": 64,
    "audio_queue_seconds": 60.0,
    "copy_min_confidence": 0.85,
    "copy_min_snr": 12.0,
    "max_events_in_snapshot": 160,
    "char_gap_units": 2.25,
    "word_gap_units": 6.5,
    "lcd_brightness_percent": 100,
    "tft_default_page": "COPY",
    "tft_screen_timeout_enabled": True,
    "tft_screen_timeout_sec": 300,
    "tft_screen_timeout_image": "/opt/morse-whisperer-pi/assets/horse_boot_splash.png",
    "cw_generator_tone_hz": 700,
    "cw_generator_wpm": 18.75,
    "cw_generator_farnsworth_wpm": 18.75,
    "cw_generator_key_profile": "computer",
    "cw_generator_playback_mode": "sound",
    "cw_generator_volume_percent": 35,
    "buttons_enabled": False,
    "button_sidecar_enabled": True,
    "show_rejected_candidates": False,
}


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path)
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        cfg.update(loaded)
    cfg["allowed_tones_hz"] = [int(x) for x in cfg.get("allowed_tones_hz", DEFAULTS["allowed_tones_hz"])]
    for key in ("sample_rate", "target_tone_hz", "web_port", "audio_blocksize"):
        cfg[key] = int(cfg[key])
    return cfg


def save_config(config: Dict[str, Any], path: str = DEFAULT_CONFIG_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    tmp.replace(p)
