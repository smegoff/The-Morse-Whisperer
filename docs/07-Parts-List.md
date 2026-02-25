# Parts List – LM358 Analog Front-End
## The Morse Whisperer

This parts list pairs with the `Wiring_Diagram_RR_OpAmp.md` front-end using an **LM358** op-amp conditioned for **ESP32 3.3 V ADC** input.

> All values shown are nominal; you can substitute nearby values if you don’t have exact parts.

---

## Overview

This document lists the core components needed to build the LM358 audio interface for the Heltec WiFi LoRa 32 V3. It’s designed to be **shop-friendly**, including parts commonly found at general electronics retailers and online.

---

## Active Component

| Qty | Part | Notes |
|:--:|------|-------|
| 1 | **LM358 Dual Op-Amp (DIP-8)** | Dual amplifier; single-supply capable; not rail-to-rail — see wiring notes |

---

## Passive Components

### Resistors (1/4 W or similar)

| Qty | Value | Purpose |
|:--:|:------:|---|
| 2 | **100 kΩ** | Mid-rail bias divider |
| 1 | **10 kΩ** | Inverting input bias resistor |
| 1 | **100 kΩ** | Feedback resistor |
| 1 | **1 kΩ** | Series resistor to ADC |

> The gain stage is set for ~11× (Rf/Rg). If you find output clipping, lower gain by reducing Rf (e.g., 47 kΩ or 60 kΩ).

---

### Capacitors

| Qty | Value | Notes |
|:--:|:------:|------|
| 1 | **10 µF (electrolytic)** | AC coupling input cap |
| 2 | **100 nF (ceramic)** | One for bias node decoupling; one for LM358 supply decoupling |
| 1 | **100 nF (optional)** | Optional ADC low-pass to ground |
| 1 | **10 µF (optional)** | Extra bias smoothing |

> Use quality caps — film preferred for coupling, ceramics for decoupling.

---

## Connectors & Misc

| Qty | Part | Notes |
|:--:|------|------|
| 1 | **3.5 mm audio jack (or similar)** | Connects audio source (headphone line) |
| 1 | **Shielded audio cable** | Short run reduces noise |
| 1 | **Breadboard / perfboard** | Build platform |
| — | **Hook-up wire** | Ground, VREF, audio, ADC |

---

## Optional Protection

| Qty | Part | Purpose |
|:--:|------|------|
| 2 | **Clamp diodes** (e.g., BAT54/BAT54S, 1N4148) | Protect ADC inputs to stay within 0–3.3 V |

**Note:** Clamp diodes are strongly recommended for safety on GPIO4 and other ADC pins.

---

## Recommended Spares (Handy To Have)

| Part | Reason |
|------|--------|
| 10 kΩ, 15 kΩ, 22 kΩ, 47 kΩ resistors | For gain tweaking |
| 1 µF, 4.7 µF, 10 µF caps | For bias network experimentation |
| Extra LM358 | Op-amp replacements if you experiment |

---

## Sourcing & Substitutions

If local electronics stores are out of stock or limited, you can source these parts from:
- Local electronics distributors (RS, Element14)
- Online hobbyist retailers (Altronics, Little Bird)
- Global suppliers (AliExpress, DigiKey, Mouser, etc.)

---

## Summary Table

| Component | Qty | Primary Function |
|-----------|:--:|------------------|
| LM358 (dual) | 1 | Front-end amplification |
| 100 kΩ resistors | 2 | Mid-rail bias |
| 10 kΩ | 1 | Gain stage reference |
| 100 kΩ | 1 | Gain stage feedback |
| 1 kΩ | 1 | ADC series protection |
| 10 µF coupling | 1 | AC audio coupling |
| 100 nF decoupling | 2 | Bias & supply stability |
| 100 nF ADC (optional) | 1 | Additional filtering |
| Clamp diodes | 2 | ADC overvoltage safety |
| 3.5 mm jack | 1 | Audio input |

---

If you want, I can also produce a **“buy list with links and prices”** (Amazon/eBay/Jaycar/other) so you can paste that into your repo’s README or shopping checklist.

---

## 📌 `docs/Schematic_LM358.md`

```md
# Schematic – LM358 Audio Front-End
## The Morse Whisperer

This document describes the front-end circuit used to convert analog CW audio into a biased, amplified signal suitable for the ESP32 ADC.

---

## 1) Power & Bias Reference
