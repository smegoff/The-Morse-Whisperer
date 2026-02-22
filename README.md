# The Morse Whisperer (Heltec WiFi LoRa 32 V3)

CW decoder for the Heltec WiFi LoRa 32 V3 with:
- Goertzel tone detector (ADC audio in)
- Adaptive dot timing + RAW/EXPANDED text
- SNR + SNR bar (OLED)
- Squelch (SNR-based gate)
- PRG button menu (single button, deterministic behaviour)
- SoftAP Wi-Fi + mobile-friendly Web UI
- LoRa radio ON/OFF toggle (OFF by default) via RadioLib (optional)
- Menu option to show a Wi-Fi join QR code (no main-screen squeeze)

## Hardware
- **Board:** Heltec WiFi LoRa 32 V3 (ESP32-S3)
- **Display:** SSD1306 128x64 OLED (on-board)
- **Audio in:** external analogue front-end recommended (see docs)

## Quick start

### 1) Install Arduino IDE + board support
- Install the Heltec ESP32 core (Heltec-esp32 core 3.x recommended).
- Select board: **Heltec WiFi LoRa 32 (V3)** (or equivalent in your core package).

### 2) Install required libraries
Required:
- **U8g2**

Optional (enables LoRa ON/OFF):
- **RadioLib** (by Jan Gromeš)

QR code support (pick ONE that matches your environment):
- If your ESP32 core provides `qrcode.h` with `esp_qrcode_*` APIs, you’re good.
- Otherwise install Richard Moore “qrcode” library (see docs/libraries.md)

### 3) Configure / Flash
- Open: `firmware/The_Morse_Whisperer/The_Morse_Whisperer.ino`
- Verify the `ADC_PIN` matches your wiring (default GPIO 4).
- Flash to the Heltec.

### 4) Connect to the Web UI
The device runs a SoftAP:
- **SSID:** The Horse Whisperer
- **Pass:** cwdecode123

Once connected:
- Open: `http://192.168.4.1/`

## Documentation
- Wiring: `docs/wiring.md`
- Breadboard build notes: `docs/breadboard-notes.md`
- Libraries: `docs/libraries.md`
- Troubleshooting: `docs/troubleshooting.md`

## Safety + sanity
The ESP32 ADC is **3.3V max** and hates negative voltage.
Use the recommended op-amp bias + gain stage, or at minimum a coupling cap + bias network.
See `docs/wiring.md`.

## License
MIT (see LICENSE).# The-Morse-Whisperer
