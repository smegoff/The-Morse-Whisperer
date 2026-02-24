# TL;DR — What is it and how does it work?

The Morse Whisperer is a CW decoder running on a Heltec WiFi LoRa 32 V3 (ESP32-S3). It samples audio via the ESP32 ADC, runs a Goertzel detector tuned to the CW tone, derives an SNR-like measure, gates the signal using squelch, then converts tone on/off timing into dots/dashes.

It maintains an adaptive estimate of dot length (ms), which produces a WPM estimate and improves decoding as the sender changes speed. Output is displayed on the OLED and via a simple Web UI over a built-in Wi-Fi access point.

Audio sampling is done in a dedicated FreeRTOS task into a ring buffer so the decoder never blocks ADC timing, and the sampler yields properly so the task watchdog doesn’t reboot the chip.
