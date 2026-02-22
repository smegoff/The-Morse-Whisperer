# Libraries

## Required
### U8g2
Install from Library Manager:
- "U8g2" by oliver

## Optional (LoRa ON/OFF)
### RadioLib
Install from Library Manager:
- "RadioLib" by Jan Gromeš

If RadioLib is missing:
- LoRa toggle will show N/A in the UI
- Sketch should still compile (by design)

## QR Code support
This sketch auto-detects `qrcode.h` and supports:
1) ESP32 core qrcode implementation (esp_qrcode_* API)
2) Richard Moore QR code library (QRCode / qrcode_* API)

### If you got errors like:
- `QRCode was not declared`
- `qrcode_getBufferSize not declared`
Then the headers present don't match the API the code is expecting.

### Recommended: Richard Moore library
In Arduino Library Manager search for:
- "qrcode" or "QRCode" by Richard Moore (RicMoo)

Make sure it provides:
- `QRCode` struct
- `qrcode_initText`
- `qrcode_getModule`
- `qrcode_getBufferSize`
