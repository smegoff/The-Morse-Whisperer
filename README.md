# The Morse Whisperer

The Morse Whisperer is a Raspberry Pi based CW / Morse decoder appliance.

It provides:

- USB audio input
- real-time CW tone detection
- adaptive Morse timing decode
- TFT display output
- browser-based status/control UI
- built-in clean CW generator/self-test
- selectable decoder profiles for clean generated CW and real radio CW

## Decoder profiles

| Display name | Internal key | Use |
|---|---:|---|
| Clean CW | `clean` | Clean generated CW, self-test, challenge/demo operation |
| Radio CW | `kiwi` | Real radio / KiwiSDR CW with wider tone range and more tolerant gates |

Switch from the command line:

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py clean
sudo systemctl restart morse-whisperer.service
```

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py kiwi
sudo systemctl restart morse-whisperer.service
```

Show the current profile:

```bash
/opt/morse-whisperer-pi/tools/set_decoder_profile.py show
```

The web UI also has a Decoder Profile selector. Switching profiles from the web UI saves the selected profile, restarts the service, reloads the selected profile, and clears runtime decode state.

## Clean CW verification

```bash
curl -sS -X POST http://127.0.0.1:8080/api/cw/selftest \
  -H 'Content-Type: application/json' \
  -d '{"text":"CQ CQ DE ZL1SXG ZL1SXG K","tone_hz":700,"wpm":18.75,"farnsworth_wpm":18.75,"key_profile":"computer","start_delay_ms":250,"end_gap_ms":1000,"volume_percent":50}' \
  | python3 -m json.tool
```

Expected:

```text
status: PASS
decoded: CQ CQ DE ZL1SXG ZL1SXG K
```

## TFT profile label

The TFT COPY page shows the active profile:

```text
STABLE COPY CLEAN
STABLE COPY RADIO
```

## Important troubleshooting note

If the self-test passes but live CW does not decode, check the audio path first. In testing, the major “deaf decoder” fault was a physical audio cable/connection issue, not the decoder engine.

## Main service

```bash
sudo systemctl status morse-whisperer.service --no-pager -l
sudo systemctl restart morse-whisperer.service
```

## Web UI

```text
http://<pi-ip>:8080
```

Local API check:

```bash
curl -sS http://127.0.0.1:8080/api/snapshot | python3 -m json.tool
```

## Hardware notes

Known TFT button mapping on this build:

| Button | GPIO | Short press | Hold |
|---:|---:|---|---|
| 1 | GPIO23 | Page | Freeze |
| 2 | GPIO22 | Scan | Restart |
| 3 | GPIO27 | Reset | Full reset |
| 4 | GPIO18 | Clear | Full reset |

Avoid reusing LCD control pins for buttons or other GPIO functions.
