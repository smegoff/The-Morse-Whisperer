# Operating Guide

## Check service

```bash
systemctl is-active morse-whisperer.service
sudo systemctl status morse-whisperer.service --no-pager -l
```

## Check profile

```bash
/opt/morse-whisperer-pi/tools/set_decoder_profile.py show
```

## Clean CW mode

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py clean
sudo systemctl restart morse-whisperer.service
```

Run self-test:

```bash
curl -sS -X POST http://127.0.0.1:8080/api/cw/selftest \
  -H 'Content-Type: application/json' \
  -d '{"text":"CQ CQ DE ZL1SXG ZL1SXG K","tone_hz":700,"wpm":18.75,"farnsworth_wpm":18.75,"key_profile":"computer","start_delay_ms":250,"end_gap_ms":1000,"volume_percent":50}' \
  | python3 -m json.tool
```

## Radio CW mode

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py kiwi
sudo systemctl restart morse-whisperer.service
```

Then feed receiver/KiwiSDR audio into the USB audio input.

## Useful live snapshot

```bash
SNAP="$(curl -sS --max-time 5 http://127.0.0.1:8080/api/snapshot)"

python3 - <<'PY' "$SNAP"
import json, sys
s=json.loads(sys.argv[1])
d=s.get("decode",{}) or {}
q=s.get("quality",{}) or {}
a=s.get("audio",{}) or {}

print("audio:", a.get("level_status"), "rms", a.get("rms"), "peak", a.get("peak"), "clip", a.get("clipping_percent"))
print("tone:", q.get("selected_tone_hz"), "target:", q.get("target_tone_hz"), "mode:", q.get("tone_mode"))
print("snr:", q.get("snr_db"), "confidence:", q.get("confidence"), "reason:", q.get("reason"))
print("symbols:", q.get("decoded_symbols"), "failed:", q.get("failed_symbols"), "marks:", q.get("marks"), "spaces:", q.get("spaces"), "wpm:", q.get("wpm"))
print("stable_copy:", repr(d.get("stable_copy") or ""))
print("raw:", repr(d.get("stable_raw") or d.get("raw") or ""))
print("ranking:", (q.get("tone_ranking") or [])[:10])
PY
```

## Audio troubleshooting

If self-test passes but live copy is empty:

1. Check the audio cable.
2. Check the browser/KiwiSDR output volume.
3. Check ALSA capture gain.
4. Record a WAV directly from the device.

```bash
arecord -D plughw:2,0 -r 8000 -f S16_LE -c 1 -d 12 /tmp/live-cw-test.wav
```

## Web profile switching

The web UI profile switch requires permission to restart `morse-whisperer.service`.

A polkit rule is used to allow the service user/group to restart only that unit:

```text
/etc/polkit-1/rules.d/49-morse-whisperer-profile-restart.rules
```
