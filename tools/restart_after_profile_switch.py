#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import time
import urllib.request
from pathlib import Path

RESTART_LOG = Path("/tmp/mw-profile-restart.log")
RESET_LOG = Path("/tmp/mw-profile-reset.log")
RESET_URL = "http://127.0.0.1:8080/api/reset"


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with RESTART_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def main() -> int:
    RESTART_LOG.write_text("", encoding="utf-8")
    RESET_LOG.write_text("", encoding="utf-8")
    time.sleep(1)

    restart = subprocess.run(
        ["/bin/systemctl", "restart", "morse-whisperer.service"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    if restart.stdout:
        with RESTART_LOG.open("a", encoding="utf-8") as handle:
            handle.write(restart.stdout)
    if restart.returncode != 0:
        log(f"restart failed with exit code {restart.returncode}")
        return restart.returncode

    log("service restarted; waiting for decoder reset API")
    for _ in range(30):
        try:
            request = urllib.request.Request(RESET_URL, data=b"{}", method="POST")
            with urllib.request.urlopen(request, timeout=2) as response:
                body = response.read().decode("utf-8", "replace")
            RESET_LOG.write_text(body + "\n", encoding="utf-8")
            log("decoder reset completed")
            return 0
        except Exception as exc:
            RESET_LOG.write_text(str(exc) + "\n", encoding="utf-8")
            time.sleep(1)

    log("decoder reset API did not recover within 30 seconds")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
