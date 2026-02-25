# The Morse Whisperer
## Analog Front-End – LM358 (Jaycar-Friendly Build)

---

## Table of Contents
* [Overview](#overview)
* [Why LM358 (and the one big gotcha)](#why-lm358-and-the-one-big-gotcha)
* [Signal Flow Architecture](#signal-flow-architecture)
* [Full Wiring Diagram](#full-wiring-diagram)
* [Heltec V3 Connections](#heltec-v3-connections)
* [LM358 Pinout](#lm358-pinout)
* [Pin-by-Pin Wiring Checklist](#pin-by-pin-wiring-checklist)
* [Parts List](#parts-list)
* [Voltage Sanity Checks](#voltage-sanity-checks)
* [Troubleshooting](#troubleshooting)

---

## Overview

This front-end conditions CW audio for the ESP32-S3 ADC on the **Heltec WiFi LoRa 32 V3**.

It performs:

1. **AC coupling** of input audio
2. **Mid-rail bias** generation (≈ **1.65 V** referenced to 3V3)
3. **Non-inverting gain stage**
4. **ADC protection** (series resistor + clamp diodes recommended)

All designed to run “makers night style” on a breadboard with parts you can actually buy locally.

---

## Why LM358 (and the one big gotcha)

LM358 is common and cheap. It works well for single-supply audio-ish stuff.

**Gotcha:** LM358 is **not rail-to-rail output** on 3.3 V. If you power it from 3.3 V, the output can run out of headroom near the top rail and you’ll clip.

**Solution used here (recommended):**
- Power the **LM358 from 5 V (VBUS/5V)** so it has headroom.
- Keep the **signal bias at ~1.65 V from 3V3**, because the ADC is 0–3.3 V.
- Add a **series resistor + clamp diodes to 3V3/GND** so the ADC never gets bullied above 3.3 V.

This gives you a stable, forgiving front-end without needing unicorn parts.

---

## Signal Flow Architecture

AUDIO_IN
│
▼
AC Coupling Capacitor (10uF)
│
▼
Biased Node (~1.65V from 3V3 divider)
│
▼
LM358 Non-Inverting Amplifier (~6–11× typical)
│
▼
1k Series Protection + Clamp
│
▼
ESP32 ADC (GPIO4)


---

## Full Wiring Diagram

### 1) Bias generator (from 3V3)
3V3 --- R1 100k ---+--- R2 100k --- GND
|
BIAS (~1.65V)
|
C_BIAS 100nF
|
GND


Optional but recommended: add a **10uF** from BIAS to GND as well (makes it quieter).

---

### 2) Input coupling into biased domain
AUDIO TIP --- C_IN 10uF --- AC_NODE -----> LM358 IN+ (Pin 3)
|
BIAS (tie AC_NODE to BIAS)
AUDIO SLEEVE ----------------- GND


**Electrolytic orientation:** **+** towards the LM358 / biased node.

---

### 3) Gain stage (Non-inverting)
LM358 A:
IN+ (Pin 3) = AC_NODE (audio + bias)
IN- (Pin 2) = feedback node
OUT (Pin 1) = amplified output

Pin 2 (IN-) --- Rg 10k --- BIAS
Pin 1 (OUT) --- Rf 100k -- Pin 2 (IN-)

Gain ≈ 1 + (Rf/Rg) ≈ 11×


If your audio source is “hot” and you clip, drop gain by changing values, eg:
- Rf = 47k, Rg = 10k  → ~5.7×
- Rf = 33k, Rg = 10k  → ~4.3×

---

### 4) ADC protection + optional filtering
LM358 OUT (Pin 1) --- R_SER 1k --- ADC_IN ---> Heltec GPIO4

Optional low-pass:
ADC_IN --- C_ADC 100nF --- GND

Recommended clamp (keeps ADC safe):
ADC_IN ---|<|--- 3V3
ADC_IN ---|>|--- GND
(BAT54 / BAT54S / 1N5819 / even 1N4148 in a pinch)


---

## Heltec V3 Connections

Your firmware uses:

```cpp
const int ADC_PIN = 4;

So GPIO4 must receive ADC_IN.

Power:

LM358 V+ → 5V / VBUS (from Heltec 5V pin or USB 5V rail)

LM358 GND → GND

Bias divider uses 3V3:

BIAS network top → 3V3

BIAS network bottom → GND

Signal:

ADC_IN → GPIO4

If your Heltec breakout doesn’t expose 5V nicely: you can still run LM358 from 3V3, but expect earlier clipping. The 5V method is the “stop being sad” option.

LM358 Pinout

DIP-8, notch at the top:

        ________
  OUTA |1     8| V+
  INA- |2     7| OUTB
  INA+ |3     6| INB-
   GND |4     5| INB+
        --------

Pin-by-Pin Wiring Checklist
Power

Pin 8 (V+) → 5V / VBUS

Pin 4 (GND) → GND

Decoupling: 100nF from Pin 8 to Pin 4 (as close as possible)

Bias

R1 100k: 3V3 → BIAS

R2 100k: BIAS → GND

C_BIAS 100nF: BIAS → GND

(Optional) 10uF: BIAS → GND

Input

Audio tip → 10uF cap → Pin 3 (IN+)

Audio sleeve → GND

Tie Pin 3 (IN+) to BIAS (same node as the bias midpoint)

Gain

Pin 2 (IN-) → Rg 10k → BIAS

Pin 1 (OUT) → Rf 100k → Pin 2 (IN-)

Output / ADC

Pin 1 (OUT) → 1k series → ADC_IN

ADC_IN → GPIO4

Optional: ADC_IN → 100nF → GND

Recommended: clamp diodes from ADC_IN to 3V3 and GND

Unused op-amp (B channel) — do NOT leave floating

Do a quiet unity follower at mid-rail:

Pin 5 (INB+) → BIAS

Pin 6 (INB-) → Pin 7 (OUTB)

Parts List
IC

LM358 (DIP-8)

Resistors

100k ×2 (bias divider)

10k ×1 (Rg)

100k ×1 (Rf)

1k ×1 (ADC series)

Capacitors

10uF electrolytic ×1 (input coupling)

100nF ×2 (bias filter + op-amp decoupling)

Optional: 100nF ×1 (ADC low-pass)

Optional: 10uF ×1 (extra bias smoothing)

Optional protection

BAT54 / BAT54S / 1N5819 / 1N4148 ×2 (ADC clamp)

Voltage Sanity Checks

With power on and no audio:

Node	Expected
3V3	~3.3 V
5V/VBUS	~5.0 V (if USB powered)
BIAS	~1.65 V
LM358 OUT (Pin 1)	~1.65 V
ADC_IN	~1.65 V

With audio present:

Signal should swing around ~1.65 V

ADC_IN should never exceed 3.3 V (clamps help guarantee this)

Troubleshooting
Symptom	Likely Cause	Fix
Reboots / weird ADC behaviour	ADC seeing >3.3 V	Add clamp diodes + keep 1k series
Always decoding / “stuck tone”	Too much gain / noise	Lower gain (Rf down) + improve grounding
Deaf / no decode	Too little gain / wrong ADC pin	Confirm GPIO4 + raise gain slightly
Distorted / harsh decode	Clipping	Power LM358 from 5V and/or lower gain
Noisy, unstable thresholds	Bias not clean	Add 10uF on BIAS, keep 100nF close
