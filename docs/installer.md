# Installer Guide

The installer must be run from a complete repository checkout because it copies
the application, profiles, assets, tools, and service files.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/smegoff/The-Morse-Whisperer.git
cd The-Morse-Whisperer
sudo ./install.sh
```

It performs these steps:

1. Installs Python, Flask, NumPy, Pillow, ALSA utilities, NetworkManager, Polkit and LCD-friendly fonts.
2. Creates the `morsewhisperer` system user.
3. Installs the app to `/opt/morse-whisperer-pi`.
4. Creates a Python virtual environment.
5. Installs systemd services.
6. Installs the Polkit rule for Wi-Fi management.
7. Preserves an existing appliance `config.json` during rebuilds.
8. Starts the appliance service.

The known-good TFT overlay is documented in `docs/tft-display.md`; the installer
does not rewrite `/boot/firmware/config.txt` automatically.
