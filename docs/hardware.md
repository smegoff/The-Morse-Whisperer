# Hardware Guide

Known-good target:

- Raspberry Pi 4
- GoodTFT/Jaycar XC9022-style 2.8 inch SPI TFT
- USB audio dongle with mic input and headphone/speaker output
- Optional powered speaker or headphones for trainer output

## LCD GPIO warnings

The XC9022/GoodTFT screen uses important GPIO pins:

- GPIO24 is touchscreen PENIRQ
- GPIO25 is LCD DC on the verified working overlay
- GPIO22/GPIO27 are used by alternate TFT overlays and should remain reserved

Do not use GPIO22, GPIO24, GPIO25, or GPIO27 for physical buttons. Touchscreen
input is exposed through ADS7846, normally `/dev/input/event1`, and should be
preferred for soft-button work.

## Audio wiring

Use USB audio for input. Do not feed radio speaker-level audio directly into the Pi GPIO.
