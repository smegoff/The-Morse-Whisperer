# Wiring & Breadboard Layout
For standard 1–30 / A–E F–J split breadboard

---

## Why Biasing Is Required

The ESP32 ADC cannot read negative voltages.

Audio is AC and swings positive and negative.

We must:
1. AC-couple the signal
2. Bias it to ~1.65V (mid-rail)
3. Limit voltage into ADC

---

# Circuit Overview

Audio In → AC Coupling → Bias Node (~1.65V) → Series Resistor → ADC Pin

Bias node created by 100k / 100k divider from 3.3V to GND.

---

# Component List

| Part | Value |
|------|-------|
| R1 | 100k |
| R2 | 100k |
| R3 | 10k |
| C1 | 100nF–1µF |
| C2 | 10nF–100nF (optional smoothing) |
| Optional | 2x 1N4148 clamp diodes |

---

# Breadboard Coordinates

We will use:

Row 15 = Bias Node  
Row 16 = ADC Node  
Row 14 = Audio In  

Top rails:
- Red = 3.3V
- Blue = GND

---

## Step-by-Step Placement

### 1) Power Rails

ESP32 3V3 → Red rail  
ESP32 GND → Blue rail  

---

### 2) Bias Divider

R1 (100k)
- One leg in red rail
- Other leg in Row 15 (A)

R2 (100k)
- One leg in Row 15 (B)
- Other leg in blue rail

Bias node now exists across Row 15 (A–E).

Optional:
C2 from Row 15 → Blue rail

---

### 3) AC Coupling

C1 from:
- Row 14 (Audio Tip input)
- Row 15 (Bias node)

Audio ground → Blue rail

---

### 4) ADC Feed

R3 (10k)
- One leg in Row 15
- Other leg in Row 16

Row 16 → Jumper → GPIO4 (ADC pin)

---

## ASCII Top View (Left Half Only)

Columns A–E

Top Rails:
+3.3V ===================================
GND ===================================

Row 14: Audio Tip → C1 → Row 15
Row 15: Bias Node
R1 → +3.3V
R2 → GND
(C2 → GND optional)
R3 → Row 16
Row 16: ADC Node → GPIO4


---

## Optional Protection Diodes

At Row 16 (ADC node):

D1:
- Cathode to 3.3V rail
- Anode to ADC node

D2:
- Anode to GND rail
- Cathode to ADC node

Prevents over-voltage spikes.

---

# Audio Level Guidance

Target:
~300–800mV peak-to-peak at ADC.

If decoding is random:
- Audio too loud (clipping)
- Add attenuation

If decoding misses:
- Audio too weak
- Reduce squelch slightly

---

# Final Checklist

- [ ] 3.3V connected
- [ ] GND connected
- [ ] Bias divider installed
- [ ] AC coupling capacitor installed
- [ ] Series resistor installed
- [ ] ADC pin connected
- [ ] Audio ground connected
- [ ] No negative voltage reaching ADC

---

This wiring is stable and RF-safe for real-world CW decoding.
