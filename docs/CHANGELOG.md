# Changelog

## 2026-06-17 Radio QRN update

- Added a Radio-only impulse blanker for short static/QRN spikes before the
  existing tone/envelope decoder.
- Added conservative Radio-only event cleanup for tiny dropouts inside marks
  and isolated noise marks.
- Added regression coverage showing noisy impulse audio recovers with the
  blanker while Clean-profile switching removes Radio-only keys.

## 2026-06-14 Radio acquisition update

- Added keyed-envelope tone scoring for Radio CW so steady carriers no longer
  win solely through raw power.
- Added 5 Hz fine search around the strongest coarse tone candidates.
- Added relative weak-signal activity detection and guarded tone relocking.
- Bounded tone scoring to recent audio to keep long sessions responsive.
- Added a near-silence pre-analysis gate to keep Radio mode lightweight while
  retaining signals above the appliance noise floor.
- Added synthetic weak-signal/interference regression tests and a labelled WAV
  evaluation tool.
- Kept Clean CW on the original tone-selection path.

## 2026-06-14

- Preserved display and button controller references across decoder resets.
- Made profile writes atomic and limited switching to decoder tuning keys.
- Replaced the inline profile-restart shell command with a Python helper.
- Preserved live `config.json` during installer rebuilds.
- Added service audio/video groups and optional AI environment loading to the
  installed unit.
- Added runtime regression tests, an API smoke test, and deployment/security
  documentation.

## 2026-05-24

### Added

- Decoder profiles:
  - Clean CW
  - Radio CW
- CLI profile switcher:
  - `tools/set_decoder_profile.py`
- Web UI Decoder Profile selector
- Web profile switching with service restart and decoder reset/clear
- Radio CW profile tone range up to 2000 Hz
- TFT COPY page profile indicator:
  - `STABLE COPY CLEAN`
  - `STABLE COPY RADIO`
- One-shot installer support for:
  - profile files
  - profile switch permissions
  - systemd services
  - validation
- Documentation:
  - README
  - Installation
  - Decoder profiles
  - Operating guide
  - Recovery guide

### Verified

- Clean CW self-test passes.
- Clean generated CW decodes correctly.
- Real radio CW decodes successfully in Radio CW mode.
- Profile switching works from command line and web UI.

### Notes

The major live decode fault encountered during testing was a physical audio cable/connection issue, not the decoder engine.
