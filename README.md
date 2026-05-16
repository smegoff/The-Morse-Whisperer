# The Morse Whisperer

A Raspberry Pi 4 CW decoder appliance with USB audio, a 320x240 SPI TFT, a web UI, Wi-Fi setup tools, and a CW trainer.

This repository is now focused on the Raspberry Pi appliance build. Older ESP32/Heltec notes have been replaced by the Pi codebase and installer.

## Quick install

On Raspberry Pi OS Lite:

```bash
curl -fsSL https://raw.githubusercontent.com/smegoff/The-Morse-Whisperer/main/install.sh | sudo bash
```

Reboot when prompted, then open:

```text
http://<pi-ip>:8080
```

## What you get

- Live CW decode from USB audio input
- Goertzel tone detector with tone ranking
- Stable COPY and RAW views
- 320x240 TFT display output using `/dev/fb1`
- Web UI with settings, trainer, and network setup
- CW generator / trainer with USB audio output
- Animated boot splash and idle TFT splash
- NetworkManager Wi-Fi connect support from the web UI
- systemd services for boot startup

## Known-good hardware

- Raspberry Pi 4
- Raspberry Pi OS Lite / Debian 64-bit
- GoodTFT / Jaycar XC9022-style 2.8 inch SPI TFT
- USB sound card with capture and playback

Known-good audio device:

```text
audio_device:        plughw:2,0
audio_output_device: plughw:2,0
```

Known-good TFT overlay:

```text
dtparam=spi=on
dtoverlay=pitft28-resistive,rotate=90,speed=32000000,fps=20
```

## Documentation

- [Quick Start](docs/quick-start.md)
- [Hardware Guide](docs/hardware.md)
- [Installer Guide](docs/installer.md)
- [TFT Display](docs/tft-display.md)
- [Audio Setup](docs/audio.md)
- [Web UI](docs/web-ui.md)
- [Network and Wi-Fi](docs/network.md)
- [CW Trainer](docs/trainer.md)
- [Backup and Recovery](docs/backup-recovery.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Developer Notes](docs/developer-notes.md)

## License

MIT. See [LICENSE](LICENSE).
