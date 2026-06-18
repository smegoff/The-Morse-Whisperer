# The Morse Whisperer

The Morse Whisperer is a Raspberry Pi based CW / Morse decoder appliance for both clean generated CW and real radio CW.

It provides:

- USB audio input
- real-time CW tone detection
- adaptive Morse timing decode
- TFT display output
- browser-based status/control UI
- built-in clean CW generator/self-test
- CQ Rag Chew listen-only foundation for assisted operating experiments
- separate decoder profiles for clean generated CW and radio/KiwiSDR CW
- web and command-line profile switching
- TFT mode indicator showing `STABLE COPY CLEAN` or `STABLE COPY RADIO`

## Quick start

Install or rebuild from a repo checkout:

```bash
git clone https://github.com/smegoff/The-Morse-Whisperer.git
cd The-Morse-Whisperer
sudo ./install.sh
```

On rebuilds, the installer preserves the appliance's existing
`/opt/morse-whisperer-pi/config.json`.

Open the web UI:

```text
http://<pi-ip>:8080
```

Check service health:

```bash
systemctl is-active morse-whisperer.service
curl -sS http://127.0.0.1:8080/api/snapshot | python3 -m json.tool
```

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

Profile switching changes decoder tuning only. Hardware, operator, network,
display, generator, and AI settings are preserved.

## Clean CW verification

Run:

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

## Radio CW verification

Switch to Radio CW, feed receiver/KiwiSDR audio into the USB audio input, and inspect the live snapshot:

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py kiwi
sudo systemctl restart morse-whisperer.service

curl -sS http://127.0.0.1:8080/api/snapshot | python3 -m json.tool
```

Useful fields:

- `audio.level_status`
- `quality.selected_tone_hz`
- `quality.snr_db`
- `quality.confidence`
- `decode.stable_copy`

## TFT display

The COPY page shows the active profile:

```text
STABLE COPY CLEAN
STABLE COPY RADIO
```

Known TFT button mapping on this build:

| Button | GPIO | Short press | Hold |
|---:|---:|---|---|
| 1 | GPIO23 | Page | Freeze |
| 2 | GPIO22 | Scan | Restart |
| 3 | GPIO27 | Reset | Full reset |
| 4 | GPIO18 | Clear | Full reset |

Avoid reusing LCD control pins for buttons or other GPIO functions.

## Network trust

The web UI listens on the appliance network interface and does not currently
provide authentication. Use it only on a trusted LAN. Do not port-forward TCP
8080 or expose the appliance directly to the internet.

## Important troubleshooting note

If the self-test passes but live CW does not decode, check the audio path first. During testing, the major “deaf decoder” fault was a physical audio cable/connection issue, not the decoder engine.

## Documentation

- [Installation](docs/installation.md)
- [Operating Guide](docs/operating-guide.md)
- [Decoder Profiles](docs/decoder-profiles.md)
- [Recovery Guide](docs/recovery.md)
- [Changelog](docs/CHANGELOG.md)
- [CQ Rag Chew](docs/cq-rag-chew.md)
