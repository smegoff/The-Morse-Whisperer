#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
from pathlib import Path

APP = Path(os.environ.get("MW_APP_DIR", "/opt/morse-whisperer-pi"))
CONFIG = APP / "config.json"
PROFILES = APP / "profiles"
PROFILE_SWITCH_BACKUPS = APP / "patch-backups" / "profile-switch-runtime"

PROFILE_NAMES = {
    "clean": "Clean CW",
    "kiwi": "Radio CW",
}

PROFILE_KEYS = {
    "allowed_tones_hz",
    "audio_filter_mode",
    "audio_filter_narrow_hz",
    "copy_max_failed_symbols",
    "copy_min_confidence",
    "copy_min_decoded_symbols",
    "copy_min_snr",
    "decode_window_sec",
    "decoder_profile",
    "decoder_profile_name",
    "target_tone_hz",
    "threshold_bias",
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
    profile_values = load_json(src)
    new = dict(current)

    for key in PROFILE_KEYS:
        if key in profile_values:
            new[key] = profile_values[key]

    new["decoder_profile"] = profile
    new["decoder_profile_name"] = PROFILE_NAMES[profile]

    PROFILE_SWITCH_BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = PROFILE_SWITCH_BACKUPS / f"config-before-{profile}-{stamp}.json"
    backup.write_text(json.dumps(current, indent=2) + "\n")
    tmp = CONFIG.with_suffix(CONFIG.suffix + ".tmp")
    tmp.write_text(json.dumps(new, indent=2) + "\n")
    os.replace(tmp, CONFIG)

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
