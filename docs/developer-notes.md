# Developer Notes

The code is intentionally simple and service-friendly.

Main components:

- `morse_whisperer/app.py` starts audio capture, decode loop, TFT display, and Flask.
- `morse_whisperer/dsp.py` contains Goertzel tone scoring and Morse event decoding.
- `morse_whisperer/audio.py` captures ALSA raw audio into a ring buffer.
- `morse_whisperer/display.py` renders directly to the framebuffer.
- `morse_whisperer/web.py` contains the web UI and JSON API.
- `tools/network_connect_helper.py` wraps NetworkManager operations.

The repo intentionally does not include virtual environments, patch backups, logs, NetworkManager Wi-Fi secrets, or machine-specific backup files.
