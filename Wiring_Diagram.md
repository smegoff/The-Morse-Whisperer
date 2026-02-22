# Wiring Diagram (Heltec WiFi LoRa 32 V3 + OP07CP Front‑End)

This wiring diagram matches the **OP07CP breadboard front-end** (3.3V single-supply, biased ADC input) used by **The Morse Whisperer** sketch.

It’s designed for **audio/CW-ish tones** (e.g., from a receiver headphone/line out), conditioned into the ESP32 ADC range (0–3.3V) by biasing the signal around **mid-rail (~1.65V)**.

---

## TL;DR signal path

**Radio audio out** → **10µF coupling cap** → **OP07CP non-inverting amp (≈11× gain)** → **1k series** → **Heltec ADC (GPIO4)**  
Bias network holds the “zero” point at **~1.65V** so the ADC never sees negative voltage.

---

## Pin mapping (Heltec WiFi LoRa 32 V3)

| Function | Heltec pin | Notes |
|---|---|---|
| 3.3V | **3V3** | Power for the OP07CP + bias divider |
| Ground | **GND** | Common ground for everything |
| ADC input | **GPIO4** | Must match the sketch (`ADC_PIN = 4`) |

> Use the **labelled 3V3 and GND pins on the Heltec header** (don’t pull from VEXT unless you know exactly what you’re doing).

---

## OP07CP (DIP‑8) pinout (top view)

Notch at the top, pins count **counter‑clockwise**:

```
        ┌───────┐
  1  OFF│•     │OFF 8
  2  -IN│      │V+  7
  3  +IN│ OP07 │OUT 6
  4  V- │      │OFF 5
        └───────┘
```

We use:
- **Pin 7 (V+) → 3V3**
- **Pin 4 (V−) → GND**
- **Pin 3 (+IN) → BIAS + coupled audio**
- **Pin 2 (−IN) → gain network**
- **Pin 6 (OUT) → ADC via 1k**

Pins 1/5/8 (offset null) are unused.

---

## Connection list (net-by-net)

### Power + decoupling
- Heltec **3V3** → OP07 **pin 7 (V+)**
- Heltec **GND** → OP07 **pin 4 (V−)**
- **100nF** ceramic between OP07 **pin 7 (V+)** and **GND** (physically close to the chip)
- **10µF** electrolytic across **3V3 ↔ GND** near the op-amp (breadboards are noisy gremlins)

### Mid-rail bias (BIAS ≈ 1.65V)
- **100k** from **3V3 → BIAS**
- **100k** from **BIAS → GND**
- **100nF** from **BIAS → GND** (stabilises the bias node)

### Audio input coupling
- Radio audio “hot” (tip) → **10µF** electrolytic → **OP07 pin 3 (+IN)**
  - Electrolytic orientation: **+ side toward the OP07/bias** (because bias sits above 0V)
- Radio audio ground (sleeve) → **GND**

Also connect:
- **OP07 pin 3 (+IN) → BIAS** (same node)

### Gain network (non-inverting, gain ≈ 11×)
- **10k (Rg)** from **OP07 pin 2 (−IN) → BIAS**
- **100k (Rf)** from **OP07 pin 6 (OUT) → OP07 pin 2 (−IN)**

### Output to ESP32 ADC (protect + smooth)
- OP07 **pin 6 (OUT)** → **1k** series → Heltec **GPIO4 (ADC)**
- Optional but recommended: **100nF** from **GPIO4 → GND** (simple low-pass / smoothing)

---

## Diagrams

### Schematic
![OP07 schematic](docs/schematic_op07.png)

### Breadboard layout (1–30, A–E / F–J split)
![Breadboard layout](docs/breadboard_layout_op07.png)

### Breadboard layout (annotated)
![Breadboard layout annotated](docs/breadboard_layout_op07_annotated.png)

---

## Gotchas (because physics hates breadboards)

- **OP07CP is not rail-to-rail.** On 3.3V it’s fine for *small* biased audio swings, but don’t expect it to hit 0V or 3.3V cleanly.
- Keep **all grounds common** (radio audio ground must tie to Heltec ground).
- If your source is *hot* (headphone output), reduce gain:
  - swap Rf 100k → 47k (gain ≈ 5.7×), or
  - add a 10k pot as an input trim.
- ESP32 ADC is noisy. The **1k + 100nF** at the ADC pin helps a lot.

---

## Quick checkout with a multimeter

Before plugging in audio:
1. Power the Heltec.
2. Measure **BIAS** to GND: should be **~1.65V**.
3. Measure OP07 output (pin 6) to GND: should also idle around **~1.65V**.
4. If BIAS is wrong (0V or 3.3V), stop and check the 100k/100k divider wiring.

---

## Where this connects in firmware

The sketch expects the conditioned audio on:

```cpp
static const int ADC_PIN = 4;
```

So make sure your ADC wire lands on **GPIO4**.
