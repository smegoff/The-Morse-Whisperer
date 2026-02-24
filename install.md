# Install (Firmware)

## Requirements
- Arduino IDE or PlatformIO
- Board: Heltec WiFi LoRa 32 (V3) / ESP32-S3
- Libraries:
  - U8g2 (OLED)
  - WiFi, WebServer (ESP32 core)
  - RadioLib (optional, for LoRa)
  - qrcode.h (optional, for QR screen — ESP32 core QR or RicMoo QR library)

## Arduino IDE setup
1. Install ESP32 board support (Heltec/ESP32 core appropriate for V3 / S3).
2. Select board: **Heltec WiFi LoRa 32(V3)** (or ESP32S3 Dev Module if that’s what your core provides).
3. Ensure PSRAM setting matches your board config (Heltec V3 often has PSRAM).
4. Install libraries via Library Manager:
   - U8g2
   - (Optional) RadioLib
5. Open `firmware/morse_whisperer.ino`
6. Compile and upload.

## First boot checks
On Serial (115200):
- You should see AP SSID and IP.
- You should NOT see task watchdog resets.
- You should see calibration output if training auto-calibrates at boot.

## Hardware warning (ADC input)
The ESP32 ADC expects a 0–3.3V-ish range. Your audio must be:
- AC-coupled,
- biased to mid-rail (≈1.65V),
- optionally amplified and limited/clamped.

If you feed raw audio centred around 0V, you will clip and confuse the detector.
