#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from decode_wav import read_wav
from morse_whisperer.config import load_config
from morse_whisperer.dsp import analyse_samples


def normalise(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate labelled CW WAV files.")
    parser.add_argument("manifest", help="JSON file containing cases with wav, expected, and optional profile")
    parser.add_argument("--max-error-rate", type=float, default=0.20)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", payload if isinstance(payload, list) else [])
    results = []

    for case in cases:
        wav_path = (manifest_path.parent / case["wav"]).resolve()
        profile = case.get("profile")
        config_path = Path(profile).resolve() if profile else None
        cfg = load_config(str(config_path)) if config_path else load_config()
        samples, rate, _channels, _width, _frames = read_wav(str(wav_path))
        cfg["sample_rate"] = rate
        result = analyse_samples(samples, cfg)
        expected = normalise(case.get("expected", ""))
        decoded = normalise(result.copy)
        distance = edit_distance(expected, decoded)
        error_rate = distance / max(1, len(expected))
        results.append({
            "wav": str(wav_path),
            "expected": case.get("expected", ""),
            "decoded": result.copy,
            "selected_tone_hz": result.selected_tone_hz,
            "confidence": result.confidence,
            "error_rate": error_rate,
            "pass": error_rate <= args.max_error_rate,
        })

    report = {
        "ok": bool(results) and all(item["pass"] for item in results),
        "case_count": len(results),
        "mean_error_rate": sum(item["error_rate"] for item in results) / max(1, len(results)),
        "results": results,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
