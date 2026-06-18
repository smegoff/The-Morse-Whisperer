import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = os.environ.get("MW_CONFIG", "/opt/morse-whisperer-pi/config.json")

DEFAULTS: Dict[str, Any] = {
    "sample_rate": 8000,
    "target_tone_hz": 700,
    "tone_mode": "auto",
    "allowed_tones_hz": [400,500,550,600,650,700,750,800,850,900,950,1000],
    "initial_wpm": 18.75,
    "threshold_bias": 0.48,
    "window_ms": 12,
    "hop_ms": 8,
    "event_comp_ms": 0.0,
    "decode_window_sec": 10,
    "update_interval_sec": 2,
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
    "display_rotate": 0,
    "display_refresh_sec": 1.0,
    "framebuffer_candidates": ["/dev/fb1", "/dev/fb0"],
    "lcd_brightness_percent": 55,
    "touchscreen_enabled": True,
    "touchscreen_device": "auto",
    "touchscreen_raw_x_min": 0,
    "touchscreen_raw_x_max": 4095,
    "touchscreen_raw_y_min": 0,
    "touchscreen_raw_y_max": 4095,
    "touchscreen_swap_xy": False,
    "touchscreen_invert_x": False,
    "touchscreen_invert_y": False,
    "touchscreen_footer_top": 200,
    "touchscreen_debounce_sec": 0.35,
    "station_callsign": "ZL1SXG",
    "audio_device": "auto",
    "audio_backend": "auto",
    "audio_blocksize": 64,
    "audio_queue_seconds": 20,
    "copy_min_confidence": 0.30,
    "copy_min_snr": 3.5,
    "clear_after_silence_sec": 25,
    "report_dir": "/opt/morse-whisperer-pi/reports",
    "cq_enabled": False,
    "cq_callsign": "ZL1SXG",
    "cq_cat_enabled": False,
    "cq_cat_backend": "rigctl",
    "cq_cat_model": "3073",
    "cq_cat_device": "/dev/ttyUSB0",
    "cq_cat_baud": 19200,
    "cq_band_allowlist": "40m,20m,15m,10m",
    "cq_busy_rms_threshold": 0.006,
    "cq_busy_snr_threshold_db": 6.0,
    "cq_ai_enabled": True,
    "cq_ai_provider": "gemini",
    "cq_ai_model": "gemini-2.5-flash-lite",
    "cq_allow_transmit": False,
}

def load_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    p = Path(path)
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        cfg.update(loaded)
    cfg["allowed_tones_hz"] = [int(x) for x in cfg.get("allowed_tones_hz", DEFAULTS["allowed_tones_hz"])]
    cfg["sample_rate"] = int(cfg["sample_rate"])
    cfg["target_tone_hz"] = int(cfg["target_tone_hz"])
    cfg["web_port"] = int(cfg["web_port"])
    return cfg

def save_config(config: Dict[str, Any], path: str = DEFAULT_CONFIG_PATH) -> None:
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    tmp.replace(p)

