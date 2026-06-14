# Decoder Profiles

The Morse Whisperer uses profiles so real radio tuning does not break the clean/generated CW baseline.

## Clean CW

Internal key:

```text
clean
```

Display name:

```text
Clean CW
```

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
copy_min_decoded_symbols: 5
copy_max_failed_symbols: 0
copy_min_confidence: 0.85
copy_min_snr: 12.0
decode_window_sec: 10
```

## Radio CW

Internal key:

```text
kiwi
```

Display name:

```text
Radio CW
```

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
copy_min_decoded_symbols: 3
copy_max_failed_symbols: 1
copy_min_confidence: 0.70
copy_min_snr: 7.0
decode_window_sec: 16
```

Radio CW also enables a separate signal-acquisition path:

- coarse 50 Hz search followed by 5 Hz refinement
- keyed-envelope scoring that rejects steady carriers
- relative activity detection for weak but well-keyed signals
- guarded tone relocking after repeated evidence

These settings are intentionally absent from the Clean profile, which retains
the known-good legacy tone selection behavior.

## Switching

Command-line:

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

The switcher overlays only decoder-profile tuning keys and writes
`config.json` atomically. Machine-specific and operator settings remain
unchanged. A timestamped pre-switch backup is stored under:

```text
/opt/morse-whisperer-pi/patch-backups/profile-switch-runtime/
```

## Design rule

Do not tune Clean CW to fix radio signals.

Tune only the Radio CW profile for real receiver/KiwiSDR work.

## Radio evaluation corpus

Labelled WAV files can be evaluated with:

```bash
python3 tools/evaluate_wavs.py path/to/manifest.json
```

Manifest example:

```json
{
  "cases": [
    {
      "wav": "weak-qsb-675hz.wav",
      "expected": "CQ CQ DE ZL1SXG K",
      "profile": "../../profiles/kiwi.json"
    }
  ]
}
```

The evaluator reports the selected tone, decoded text, confidence, and
character error rate for each case.
