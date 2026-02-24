# The Morse Whisperer (Heltec WiFi LoRa 32 V3)

A tiny, self-contained CW (Morse) decoder you can plonk on a bench, feed with audio, and read on OLED or a phone.

**Features**
- Goertzel tone detector (ADC audio in)
- Adaptive dot timing (WPM estimate)
- RAW + EXPANDED text output
- SNR meter + squelch gate
- PRG button menu (short/hold/panic)
- SoftAP Wi-Fi + mobile-friendly Web UI
- Optional LoRa radio ON/OFF (RadioLib if installed)
- Optional Wi-Fi join QR screen (qrcode.h supported)
- OLED power saver: sleeps after 5 mins inactivity, wakes on activity
- Buffered ADC sampler (ring buffer)
- WDT-safe sampler task (no reboot loop)
- **Training strategy modes**
  - Manual “AAAAAAAAAA” lock-in mode
  - Full auto training mode

---

## Quick start (TL;DR)
1. Flash firmware to Heltec WiFi LoRa 32 (V3).
2. Device boots a Wi-Fi AP: **The Morse Whisperer**
3. Connect and browse to: **http://192.168.4.1/**
4. Feed CW audio into the ADC input front-end.
5. Use **Calibrate** or enable **Training Mode**.

---

## Hardware notes
- This project expects a **biased, AC-coupled audio input** into the ADC (single-supply mid-rail).
- Target sample rate is 8 kHz and uses 20 ms blocks.

---

## Documentation
- [TL;DR](docs/00-TLDR.md)
- [User Manual](docs/01-User-Manual.md)
- [Install](docs/02-Install.md)
- [Technical Documentation](docs/03-Technical-Documentation.md)
- [Troubleshooting](docs/04-Troubleshooting.md)
- [Competition Mode](docs/05-Competition-Mode.md)

---

## License
MIT (or choose your flavour).
