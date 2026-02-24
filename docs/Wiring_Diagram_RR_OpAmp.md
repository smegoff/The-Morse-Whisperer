Perfect. Let’s make it look like it actually belongs in **The Morse Whisperer** repo instead of a late-night lab notebook.

Below is a cleaned, structured, GitHub-styled version with:

* Header banner
* Table of contents
* Anchored sections
* Clean section flow
* Inline diagram block
* Makers Night BOM section
* Troubleshooting
* “Why this op-amp” section

You can drop this in as:

```
docs/Wiring_Diagram_RR_OpAmp.md
```

---

# 🎧 The Morse Whisperer

## Analog Front-End – Rail-to-Rail Op-Amp (Recommended)

---

## 📖 Table of Contents

* [Overview](#overview)
* [Why Rail-to-Rail?](#why-rail-to-rail)
* [Signal Flow Architecture](#signal-flow-architecture)
* [Full Wiring Diagram](#full-wiring-diagram)
* [Heltec V3 Connections](#heltec-v3-connections)
* [Breadboard Placement (Matches Current Build)](#breadboard-placement-matches-current-build)
* [Pin-by-Pin Wiring Checklist](#pin-by-pin-wiring-checklist)
* [Parts List (Makers Night Edition)](#parts-list-makers-night-edition)
* [Voltage Sanity Checks](#voltage-sanity-checks)
* [Troubleshooting](#troubleshooting)

---

# Overview

This front-end conditions CW audio for the ESP32-S3 ADC on the **Heltec WiFi LoRa 32 V3**.

It performs:

1. AC coupling of input audio
2. Mid-rail bias generation (~1.65V)
3. Non-inverting gain stage
4. ADC protection + optional filtering

All running from **3.3V single supply**.

---

# Why Rail-to-Rail?

The ESP32 ADC expects a signal between **0V and 3.3V**.

Traditional op-amps (like OP07) struggle on 3.3V single supply.
Rail-to-rail CMOS op-amps behave properly at low voltage.

### Recommended Devices

| Part        | Type        | Notes                         |
| ----------- | ----------- | ----------------------------- |
| **MCP6002** | Dual, DIP-8 | Easiest hobby choice          |
| MCP6001     | Single      | If you don’t need bias buffer |
| TLV9002     | Dual        | Very clean modern option      |
| TLV9062     | Dual        | Faster, higher bandwidth      |
| OPA320      | Single      | Premium                       |

**Default reference build: MCP6002 (DIP-8)**

---

# Signal Flow Architecture

```
AUDIO_IN
   │
   ▼
AC Coupling Capacitor (10uF)
   │
   ▼
Biased Node (~1.65V)
   │
   ▼
Non-Inverting Amplifier (~6–11×)
   │
   ▼
1k Series Protection
   │
   ▼
ESP32 ADC (GPIO4)
```

---

# Full Wiring Diagram

```
BIAS GENERATOR
+3V3 --- R1 100k ---+--- R2 100k --- GND
                    |
                   BIAS
                    |
                  C_BIAS 100nF
                    |
                   GND


INPUT STAGE
AUDIO TIP --- C_IN 10uF --- AC_NODE ---+
                                        |
                                       IN+ (OpAmp A)
                                        |
                                       BIAS


GAIN STAGE (Non-Inverting)
IN- ---- Rg 10k ---- BIAS
OUT ---- Rf 100k ---- IN-

Gain ≈ 1 + (Rf/Rg) ≈ 11×


ADC OUTPUT
OUT --- R_SER 1k --- ADC_IN ---> GPIO4
ADC_IN --- C_ADC 100nF (optional) --- GND
```

Optional clamp protection:

```
ADC_IN ---|<|--- +3V3
ADC_IN ---|>|--- GND
```

(BAT54 Schottky recommended)

---

# Heltec V3 Connections

Only three wires required:

| Heltec Pin | Connect To  |
| ---------- | ----------- |
| 3V3        | +3V3 rail   |
| GND        | Ground rail |
| GPIO4      | ADC_IN      |

Your firmware uses:

```cpp
const int ADC_PIN = 4;
```

So GPIO4 must receive ADC_IN.

---

# Breadboard Placement (Matches Current Build)

Based on your current board photo orientation:

The DIP-8 is sitting in rows F–J around columns 27–30.

Pin mapping (dot lower-left corner):

| Pin | Location |
| --- | -------- |
| 1   | F27      |
| 2   | F28      |
| 3   | F29      |
| 4   | F30      |
| 5   | J30      |
| 6   | J29      |
| 7   | J28      |
| 8   | J27      |

For MCP6002:

| Pin | Function |
| --- | -------- |
| 1   | OUT_A    |
| 2   | IN-_A    |
| 3   | IN+_A    |
| 4   | V-       |
| 8   | V+       |

---

# Pin-by-Pin Wiring Checklist

## Power

* Pin 8 → +3V3
* Pin 4 → GND
* 100nF cap between Pin 8 and Pin 4 (close to chip)
* 10uF bulk cap between +3V3 and GND nearby

## Bias Network

* 100k from +3V3 → BIAS
* 100k from BIAS → GND
* 100nF from BIAS → GND

## Input

* Pin 3 (IN+) → BIAS
* 10uF cap from AUDIO_IN tip → Pin 3

  * Electrolytic + toward Pin 3
* Audio sleeve → GND

## Gain

* 10k from Pin 2 (IN-) → BIAS
* 100k from Pin 1 (OUT) → Pin 2

## ADC Output

* 1k from Pin 1 → ADC_IN
* ADC_IN → GPIO4
* Optional 100nF from ADC_IN → GND

## Unused Op-Amp (Amp B)

Do NOT leave floating.

Recommended:

* IN+_B → BIAS
* OUT_B → IN-_B

Unity follower at mid-rail keeps it quiet.

---

# Parts List (Makers Night Edition)

## Core

* MCP6002 (DIP-8)
* DIP socket (optional)

## Resistors

* 100k ×3
* 10k ×1
* 100k ×1 (feedback)
* 1k ×1 (ADC series)

## Capacitors

* 10uF electrolytic ×2
* 100nF ceramic ×3

## Optional

* BAT54 ×2
* 10k potentiometer (input trim)
* SOIC→DIP adapter (if needed)

---

# Voltage Sanity Checks

Before audio:

| Node   | Expected Voltage |
| ------ | ---------------- |
| BIAS   | ~1.65V           |
| OUT    | ~1.65V           |
| ADC_IN | ~1.65V           |

With audio:
Signal should swing around 1.65V without hitting 0V or 3.3V.

---

# Troubleshooting

| Symptom         | Cause                               |
| --------------- | ----------------------------------- |
| Always decoding | Too much gain                       |
| Deaf            | Not enough gain                     |
| Noisy           | Poor grounding / missing decoupling |
| Distorted       | Hitting rails (reduce gain)         |
| ADC unstable    | Add 100nF at ADC_IN                 |

---

# Final Notes

This is the preferred 3.3V-safe, rail-to-rail front-end for The Morse Whisperer.

It behaves.
It’s stable.
It won’t fight the ESP32 ADC.

Unlike certain AI schematic generators.

```

---

If you’d like, I can next generate:

- A matching **README badge section**
- A clean **SVG diagram block**
- Or a printable A4 PDF version for Makers Night

Your call.
```
