# Developer Notes

The code is intentionally simple and service-friendly.

Main components:

- `morse_whisperer/app.py` starts audio capture, decode loop, TFT display, and Flask.
- `morse_whisperer/dsp.py` contains Goertzel tone scoring and Morse event decoding.
- `morse_whisperer/audio.py` captures ALSA raw audio into a ring buffer.
- `morse_whisperer/cq.py` contains the listen-only CQ Rag Chew API and
  busy-frequency/CAT status helpers.
- `morse_whisperer/display.py` renders directly to the framebuffer.
- `morse_whisperer/web.py` contains the web UI and JSON API.
- `tools/network_connect_helper.py` wraps NetworkManager operations.
- `tools/restart_after_profile_switch.py` performs the delayed service restart
  and decoder reset without inline shell quoting.
- `tools/smoke_test.py` performs non-destructive API health checks.
- `tools/evaluate_wavs.py` measures labelled WAV files and reports character
  error rates.

The repo intentionally does not include virtual environments, patch backups, logs, NetworkManager Wi-Fi secrets, or machine-specific backup files.

Run local regression checks with:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q morse_whisperer tools
```

Radio-specific DSP must remain behind profile flags in `profiles/kiwi.json`.
The Clean profile is the protected regression baseline.
