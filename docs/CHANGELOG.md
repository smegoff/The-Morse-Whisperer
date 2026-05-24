# Changelog

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
