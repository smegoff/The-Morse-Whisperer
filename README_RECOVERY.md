# The Morse Whisperer Recovery Installer

This bundle was rebuilt from the last uploaded working source snapshot plus the Wi-Fi/network recovery patches from the ChatGPT session.

## What is included

- Python package: `morse_whisperer/`
- Tools: `tools/`
- `config.json`
- `install.sh`
- NetworkManager fallback hotspot helper
- Network Setup page with scan/connect UI
- Wi-Fi connection helper using explicit NetworkManager profiles
- Polkit rule for the `morsewhisperer` service user
- systemd services:
  - `morse-whisperer`
  - `morse-whisperer-buttons`
  - `morse-whisperer-network-fallback` installed but disabled

## Install

On a fresh Raspberry Pi OS install:

```bash
unzip morse-whisperer-recovery-installer.zip
cd morse-whisperer-recovery
sudo ./install.sh
```

Then open:

```text
http://<pi-ip>:8080
```

## Notes

The fallback hotspot service is installed but deliberately disabled. Enable only after confirming the normal web UI works:

```bash
sudo systemctl enable --now morse-whisperer-network-fallback.service
```

