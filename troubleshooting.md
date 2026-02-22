# Troubleshooting

## OLED shows LoRa: N/A
RadioLib is not installed or not detected.
- Install "RadioLib" from Library Manager.
- Recompile.

## QR errors about QRCode / qrcode_getBufferSize / ECC_LOW
You have `qrcode.h` but not the right implementation for those symbols.
- Install Richard Moore QRCode library (RicMoo), or
- Use the ESP32 core qrcode path (esp_qrcode_*).

## Decoder "hears" constant tone / garbage
Usually an analogue front-end/bias issue:
- Check GPIO 4 idle voltage ~1.65V.
- Ensure shared ground.
- Reduce gain (e.g., 47k feedback instead of 100k).

## Web UI not loading
- Connect to SSID: "The Horse Whisperer"
- Browse to: http://192.168.4.1/
- Some phones auto-switch off “no internet” Wi-Fi — tell it to stay connected.
