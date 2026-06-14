#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.request


def get_json(base_url: str, path: str) -> dict:
    with urllib.request.urlopen(base_url.rstrip("/") + path, timeout=5) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Non-destructive Morse Whisperer API smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    snapshot = get_json(args.base_url, "/api/snapshot")
    profile = get_json(args.base_url, "/api/decoder/profile")

    checks = {
        "snapshot_project": snapshot.get("project") == "The Morse Whisperer",
        "snapshot_mode": snapshot.get("mode") in {"running", "reset"},
        "profile_ok": profile.get("ok") is True,
        "profile_known": profile.get("decoder_profile") in {"clean", "kiwi"},
    }

    print(json.dumps({"ok": all(checks.values()), "checks": checks, "profile": profile}, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
