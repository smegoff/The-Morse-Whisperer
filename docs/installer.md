# Installer Guide

The installer is designed to be pasted into a fresh Raspberry Pi OS Lite SSH session.

```bash
curl -fsSL https://raw.githubusercontent.com/smegoff/The-Morse-Whisperer/main/install.sh | sudo bash
```

It performs these steps:

1. Installs Python, Flask, NumPy, Pillow, ALSA utilities, NetworkManager, Polkit and LCD-friendly fonts.
2. Creates the `morsewhisperer` system user.
3. Installs the app to `/opt/morse-whisperer-pi`.
4. Creates a Python virtual environment.
5. Installs systemd services.
6. Installs the Polkit rule for Wi-Fi management.
7. Adds the known-good TFT overlay to `/boot/firmware/config.txt`.
8. Starts the appliance service.

If the TFT overlay changed, reboot.
