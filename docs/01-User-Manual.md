# User Manual

## 1) Power on and connect
On boot, the device creates a Wi-Fi AP:

- SSID: **The Morse Whisperer**
- Pass: **cwdecode123**
- Web UI: **http://192.168.4.1/**

The OLED shows mode, tone, WPM estimate, SNR, LoRa status, and recent decoded output.

## 2) Controls

### PRG button
- **Hold ~1s**: open Menu
- **Short press**: next menu item / increment adjustment
- **Hold ~1s (inside adjust screens)**: back to menu
- **Hold ~2s**: Panic → return to main screen

### Web UI
- Toggle Training
- Calibrate
- Clear
- LoRa On/Off (if supported)
- Expand shorthand toggle
- Set Tone (Hz)
- Sensitivity slider
- Squelch slider

## 3) What “Training Mode” does
Training Mode is a helper that tries to get the decoder “locked in” quickly.

Training has **two strategies**:

### A) Manual “AAAAAAAAAA” Training (Competition mode)
This mode is designed for known-source testing (your “10 consecutive A’s” scenario).

- The device waits for a run of `A` characters.
- Once it detects **10 consecutive A decoded correctly**, it assumes:
  - tone is correct,
  - thresholds are sane,
  - dot timing is stable enough,
  - and it **stops training** (locks settings) and continues normal decoding.

This is perfect when the competition sends a known sequence before the real message.

### B) Auto Training (General use)
This mode continuously adjusts itself *until it’s stable*:
- It uses recent blocks to track signal/noise, tune thresholds, and refine dot timing.
- Once quality is stable for long enough, it “backs off” to minimal adjustments.
- If conditions change (frequency drift, level change, different sender), it can re-engage gently.

## 4) Calibrate
Calibrate listens briefly and attempts to find the strongest tone between ~400–1000 Hz (coarse + fine). It then updates the Goertzel frequency and resets detector history.

Use calibrate when:
- the tone changes,
- you move between radios,
- the input level changes significantly.

## 5) Settings
### Tone (Hz)
- Typical CW sidetone is ~600–800 Hz.
- Calibration usually gets you close, then manual tone tweak can finish.

### Sensitivity
- Higher sensitivity lowers thresholds (easier to trigger).
- If it’s decoding garbage or sticking “on”, reduce sensitivity.

### Squelch (SNRx)
- Gate that keeps the decoder quiet when there’s no meaningful signal.
- If nothing decodes, reduce squelch slightly.
- If it decodes noise, increase squelch.

## 6) Expanded text
“EXPANDED” substitutes common abbreviations (CQ, DE, 73, etc.). Turn off if you want raw contest copy.
