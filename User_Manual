# The Morse Whisperer — User Manual

## 1. Overview

The Morse Whisperer is a self-contained CW decoder that runs on the Heltec WiFi LoRa 32 V3.

It receives audio tone input, detects Morse timing using a Goertzel algorithm, and outputs decoded text via:

- OLED display
- Mobile-friendly Web UI (SoftAP mode)

---

## 2. First Power-Up

1. Connect via USB.
2. OLED splash screen appears.
3. Device creates Wi-Fi AP:

SSID: `The Morse Whisperer`  
Password: `cwdecode123`

Browse to:

http://192.168.4.1/


---

## 3. OLED Controls (Single PRG Button)

| Action | Result |
|--------|--------|
| Hold ~1 second | Enter menu / select |
| Short press | Next item |
| Hold ~2 seconds | Panic back to main screen |

---

## 4. Menu Items

- Training (auto-calibrate mode)
- Expand shorthand
- Calibrate tone
- Adjust tone (Hz)
- Adjust sensitivity
- Adjust squelch (SNR threshold)
- LoRa Radio (if RadioLib installed)
- Wi-Fi QR display
- Clear buffers
- Exit

---

## 5. Web UI Features

Displays:
- Mode (RX / TRAIN)
- Tone frequency
- WPM estimate
- SNR ratio
- RAW decode buffer
- EXPANDED decode buffer

Controls:
- Toggle Training
- Calibrate
- Clear
- Toggle LoRa
- Set tone
- Adjust sensitivity
- Adjust squelch

Updates automatically.

---

## 6. Calibration

Calibration scans for the strongest tone between ~400–1000 Hz and locks onto it.

Best results:
- Use steady sidetone
- Avoid clipping
- Avoid noisy background

---

## 7. Sensitivity & Squelch

Sensitivity:
Controls detector aggressiveness.

Squelch:
Minimum SNR required before decoding activates.

Typical starting point:
- Sensitivity: 1.0
- Squelch: 1.4

---

## 8. OLED Auto Sleep

OLED turns off after inactivity (~5 minutes).

Wakes on:
- CW tone activity
- Button press

---

## 9. Troubleshooting

Garbage decode:
- Audio clipping
- No biasing
- Excess noise

No decode:
- Squelch too high
- Tone not calibrated

OLED blank:
- VEXT polarity incorrect
- I2C pins mismatch

---

See `WIRING.md` for proper hardware setup.
