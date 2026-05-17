# The Morse Whisperer

Raspberry Pi CW decoder appliance source exported from the working appliance.

This repository is now intended to mirror the appliance code under `/opt/morse-whisperer-pi` as closely as possible. The Python package, helper tools, systemd units, Polkit rule, boot config reference, and current appliance config are taken from the appliance export.

## Install from this repository

```bash
git clone https://github.com/smegoff/The-Morse-Whisperer.git
cd The-Morse-Whisperer
sudo ./install.sh
```

Then open:

```text
http://<pi-ip>:8080
```

## Current appliance behaviour

- Main service: `morse-whisperer.service`
- Button sidecar: `morse-whisperer-buttons.service`
- App path on appliance: `/opt/morse-whisperer-pi`
- Web UI: port `8080`
- USB audio input/output configured as `plughw:2,0`
- TFT framebuffer candidates: `/dev/fb1`, then `/dev/fb0`
- Original physical button behaviour restored:
  - Button 1: PAGE / hold FREEZE
  - Button 2: SCAN / hold RESTART
  - Button 3: RESET / hold FULL RESET
  - Button 4: CLEAR / hold FULL RESET

## Important note

The source files in `morse_whisperer/` and `tools/` are copied from the working appliance export. Avoid rewriting them unless testing on the appliance confirms the change.

## Files

- `morse_whisperer/` - appliance Python package
- `tools/` - helper scripts used by the appliance
- `systemd/` - service units and drop-ins captured from the appliance
- `polkit/` - NetworkManager rule for the web Wi-Fi helper
- `boot/config.txt` - captured boot config reference
- `config.json` - appliance config snapshot
- `config.example.json` - redacted template generated during export
- `docs/EXPORT-MANIFEST.md` - export manifest and checksums

## License

MIT. See `LICENSE`.
