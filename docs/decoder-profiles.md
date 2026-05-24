# Decoder Profiles

The Morse Whisperer uses profiles so real radio tuning does not break the clean/generated CW baseline.

## Clean CW

Internal key: `clean`

Purpose:

- clean generated CW
- built-in self-test
- challenge/demo use
- stricter acceptance gates

Typical settings:

```text
tone_mode: session_auto
target_tone_hz: 700
allowed_tones_hz: 400-1000 Hz
audio_filter_mode: wide
copy_min_confidence: 0.85
copy_min_snr: 12.0
```

## Radio CW

Internal key: `kiwi`

Display name: `Radio CW`

Purpose:

- real HF CW
- KiwiSDR audio
- wider tone search
- more tolerant decode gates

Typical settings:

```text
tone_mode: session_auto
target_tone_hz: 650
allowed_tones_hz: 400-2000 Hz
audio_filter_mode: narrow
audio_filter_narrow_hz: 260
copy_min_confidence: 0.70
copy_min_snr: 7.0
decode_window_sec: 16
```

## Switching

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py clean
sudo systemctl restart morse-whisperer.service
```

```bash
sudo /opt/morse-whisperer-pi/tools/set_decoder_profile.py kiwi
sudo systemctl restart morse-whisperer.service
```

Web UI:

Use the Decoder Profile selector.

Switching profiles from the web UI saves the selected profile, restarts the service, reloads the config, and clears runtime decode state.

## Design rule

Do not tune Clean CW to fix radio signals. Tune only the Radio CW profile for real receiver/KiwiSDR work.
