# The Morse Whisperer  
CW Decoder for Heltec WiFi LoRa 32 (V3)

The Morse Whisperer is a standalone CW (Morse code) decoder built for the Heltec WiFi LoRa 32 V3.

It features:

- Goertzel-based tone detection
- Adaptive dot timing with automatic WPM estimation
- RAW and EXPANDED decoding buffers
- SNR-based squelch gating
- Single-button deterministic menu (PRG button)
- SoftAP Wi-Fi + mobile-friendly Web UI
- Optional LoRa radio control (RadioLib)
- Optional Wi-Fi QR join screen
- OLED auto-sleep power saving

---

## 📚 Documentation

- 👉 **User Manual:** [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)
- 👉 **Wiring & Breadboard Layout:** [`docs/WIRING.md`](docs/WIRING.md)

---

## 🛠 Hardware

- Heltec WiFi LoRa 32 (V3)
- Properly biased audio input (see wiring guide)
- Optional: RadioLib installed for LoRa toggle

---

## ⚠ Important

The ESP32 ADC cannot read negative voltage.

You **must** use:
- AC coupling
- Mid-rail bias (~1.65V)
- Level control

See the wiring guide for exact breadboard layout.

---

## 🧠 Philosophy

This project is designed to:
- Be stable
- Be deterministic
- Avoid menu weirdness
- Decode real on-air CW, not just lab-perfect tones

It is intentionally hardware-conscious and RF-realistic.

---

## License

Open hardware / open firmware friendly.  
Use it. Improve it. Ship it.
