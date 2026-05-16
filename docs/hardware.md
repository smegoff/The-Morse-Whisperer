# Hardware Guide

Known-good target:

- Raspberry Pi 4
- GoodTFT/Jaycar XC9022-style 2.8 inch SPI TFT
- USB audio dongle with mic input and headphone/speaker output
- Optional powered speaker or headphones for trainer output

## LCD GPIO warnings

The XC9022/GoodTFT screen uses important GPIO pins:

- GPIO22 is LCD DC
- GPIO27 is LCD RESET

Do not use GPIO22 or GPIO27 for physical buttons. Touchscreen input is normally exposed through ADS7846 on `/dev/input/event1` and should be preferred for future soft-button work.

## Audio wiring

Use USB audio for input. Do not feed radio speaker-level audio directly into the Pi GPIO.
