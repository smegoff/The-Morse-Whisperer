# Quick Start

## 1. Prepare the Pi

Install Raspberry Pi OS Lite, enable SSH, and boot the Pi on Ethernet if possible.

## 2. Run the one-shot installer

```bash
curl -fsSL https://raw.githubusercontent.com/smegoff/The-Morse-Whisperer/main/install.sh | sudo bash
```

Reboot after a fresh TFT install:

```bash
sudo reboot
```

## 3. Open the web UI

```text
http://<pi-ip>:8080
```

## 4. Check audio

```bash
arecord -l
aplay -l
speaker-test -D plughw:2,0 -t sine -f 700 -c 1 -l 1
```

## 5. Feed CW audio

Use a USB sound card input from your radio, receiver, or CW generator. Start with a clean 700 Hz tone and moderate audio level.
