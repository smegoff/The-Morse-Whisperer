#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

APP = Path("/opt/morse-whisperer-pi")
CONFIG = APP / "config.json"
PROFILES = APP / "profiles"
PROFILE_SWITCH_BACKUPS = APP / "patch-backups" / "profile-switch-runtime"

PROFILE_NAMES = {
    "clean": "Clean CW",
    "kiwi": "Radio CW",
}

def usage():
    print("Usage: set_decoder_profile.py clean|kiwi|show", file=sys.stderr)
    return 2

def load_json(path):
    return json.loads(path.read_text())

def main():
    if len(sys.argv) != 2:
        return usage()

    profile = sys.argv[1].strip().lower()

    if profile == "show":
        cfg = load_json(CONFIG)
        active = cfg.get("decoder_profile", "unknown")
        print("active decoder_profile:", active)
        print("active profile name:", PROFILE_NAMES.get(active, active))
        for k in [
            "tone_mode",
            "target_tone_hz",
            "allowed_tones_hz",
            "audio_filter_mode",
            "audio_filter_narrow_hz",
            "copy_min_decoded_symbols",
            "copy_max_failed_symbols",
            "copy_min_confidence",
            "copy_min_snr",
            "decode_window_sec",
            "word_gap_units",
        ]:
            print(f"{k}: {cfg.get(k)!r}")
        return 0

    if profile not in ("clean", "kiwi"):
        return usage()

    src = PROFILES / f"{profile}.json"
    if not src.exists():
        print(f"Profile file missing: {src}", file=sys.stderr)
        return 1

    current = load_json(CONFIG)
    new = load_json(src)

    # Preserve local hardware/runtime values from current config.
    preserve_keys = [
        "audio_device",
        "audio_output_device",
        "web_host",
        "web_port",
        "display_enabled",
        "display_width",
        "display_height",
        "display_rotate",
        "framebuffer_candidates",
        "tft_brightness_percent",
        "lcd_brightness_percent",
        "tft_idle_splash",
        "tft_idle_timeout_sec",
        "splash_enabled",
        "buttons_enabled",
        "button_page_gpio",
        "button_reset_gpio",
        "input_capture_percent",
        "ai_enabled",
        "ai_provider",
        "ai_model",
        "ai_require_confirmation",
    ]

    for k in preserve_keys:
        if k in current:
            new[k] = current[k]

    new["decoder_profile"] = profile

    PROFILE_SWITCH_BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = PROFILE_SWITCH_BACKUPS / f"config-before-{profile}-{stamp}.json"
    backup.write_text(json.dumps(current, indent=2) + "\n")
    CONFIG.write_text(json.dumps(new, indent=2) + "\n")

    print(f"decoder_profile: {profile}")
    print(f"profile_name: {PROFILE_NAMES.get(profile, profile)}")
    print(f"backup: {backup}")
    for k in [
        "tone_mode",
        "target_tone_hz",
        "allowed_tones_hz",
        "audio_filter_mode",
        "audio_filter_narrow_hz",
        "copy_min_decoded_symbols",
        "copy_max_failed_symbols",
        "copy_min_confidence",
        "copy_min_snr",
        "decode_window_sec",
        "word_gap_units",
    ]:
        print(f"{k}: {new.get(k)!r}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
