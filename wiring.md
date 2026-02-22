# Wiring (Heltec WiFi LoRa 32 V3 + OP07CP front-end)

This build biases audio around mid-rail so the ESP32 ADC only sees 0..3.3V.

## Overview
Audio In → coupling capacitor → OP07CP non-inverting gain stage (biased at 1.65V) → ESP32 ADC

- Target ADC idle voltage: ~1.65V
- Supply: 3.3V from Heltec

## Heltec pins used
- 3V3 (3.3V rail)
- GND
- ADC input: GPIO 4 (matches firmware default `ADC_PIN = 4`)

## OP07CP pinout (DIP-8, notch at top)

        _______
  1  -|•      |- 8
  2  -|        |- 7  V+
  3  -|        |- 6  OUT
  4  -|________|- 5
      V- (GND)

- Pin 7: V+ (3.3V)
- Pin 4: V- (GND)
- Pin 3: Non-inverting input (+)
- Pin 2: Inverting input (−)
- Pin 6: Output

## Step-by-step

### 1) Power + decoupling
- OP07 Pin 7 → Heltec 3V3
- OP07 Pin 4 → Heltec GND
- 100nF ceramic capacitor: between Pin 7 and Pin 4 (as close to chip as possible)

### 2) Create bias (virtual ground at 1.65V)
Two 10k resistors:

3V3 → 10k → (BIAS NODE) → 10k → GND

Add 10µF cap:
- BIAS NODE → 10µF → GND
- Electrolytic: **positive** to BIAS NODE, negative to GND

### 3) Non-inverting gain stage (gain ≈ 11×)
- BIAS NODE → OP07 Pin 3 (+ input)
- OP07 Pin 2 (− input) → 10k → GND
- OP07 Pin 6 (output) → 100k → OP07 Pin 2

Gain = 1 + (100k/10k) = 11×

### 4) Audio input coupling
- Audio source signal (tip) → 10µF capacitor → OP07 Pin 3
  - Electrolytic: **negative** to audio source, **positive** to OP07 Pin 3

Audio source ground → Heltec GND

### 5) Output to ESP32 ADC
- OP07 Pin 6 → Heltec GPIO 4 (ADC)

Optional safety:
- Add 100Ω series resistor from Pin 6 to GPIO 4.

## What to measure (multimeter)
With no audio:
- OP07 output (Pin 6) ≈ 1.65V
- GPIO 4 ≈ 1.65V

If it sits near 0V or 3.3V:
- Bias network wrong
- Op-amp miswired
- No common ground with audio source

## Notes on OP07 at 3.3V
OP07 is not rail-to-rail. For small signals it often works fine, but if you see clipping or weird behaviour,
switch to a rail-to-rail op-amp (e.g., MCP6002).
