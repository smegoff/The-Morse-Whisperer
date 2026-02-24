# Wiring Diagram – Rail-to-Rail Op-Amp Front-End (Recommended)

This wiring guide builds a stable 3.3V single-supply audio front-end for **The Morse Whisperer** on the **Heltec WiFi LoRa 32 V3**.

## Why a rail-to-rail op-amp?
ESP32 ADC wants **0–3.3V**, not a signal centred around 0V.  
So we:
1) Create a **mid-rail bias** at ~1.65V (BIAS)  
2) AC-couple the audio into that bias  
3) Amplify with a **rail-to-rail** op-amp so it behaves nicely on 3.3V

Recommended op-amps (3.3V friendly, rail-to-rail):
- **MCP6002** (dual) / MCP6001 (single) – easiest, hobby-friendly
- **TLV9002** (dual) – excellent modern choice
- **TLV9062** (dual) – faster, more “pro” but still easy
- **OPA320 / OPA333** – premium options (often pricier)

> This doc assumes a **dual op-amp** (MCP6002/TLV9002 style). We use one amp to buffer BIAS and one to amplify.

---

## Heltec Connections (what you need)
From the Heltec V3:
- **3V3** → power the op-amp + bias divider  
- **GND** → common ground  
- **GPIO4 (ADC)** → analogue input to the decoder (`ADC_PIN = 4` in your sketch)

> Use the **3V3 and GND** available on the Heltec headers.  
> GPIO4 is your ADC input in code.

---

## Circuit Overview (nets)
- **AC_IN**: Audio input (from jack tip)
- **GND**: Audio jack sleeve, Heltec GND
- **BIAS**: 1.65V reference (mid-rail)
- **AMP_OUT**: op-amp amplified output (centred at BIAS)
- **ADC_IN**: output after series resistor + optional RC filter (goes to GPIO4)

---

## Schematic (text version)

### 1) Bias generator (mid-rail) + buffer

3V3 --- R1 100k ---+--- R2 100k --- GND
|
BIAS
|
C1 100nF
|
GND

BIAS --> U1B (op-amp B) unity buffer:
U1B +IN = BIAS
U1B -IN = U1B OUT
U1B OUT = BIAS_BUF (quiet/stiff 1.65V reference)


### 2) AC coupling into biased domain (input)

Audio Jack TIP --- C2 10uF --- AC_NODE --- R3 100k --- BIAS_BUF
Audio Jack SLEEVE ------------------------------ GND


- C2 blocks DC from the source.
- R3 biases the post-cap node to mid-rail so the signal “floats” around 1.65V.

### 3) Non-inverting amplifier (gain referenced to BIAS_BUF)

U1A (op-amp A) non-inverting:
+IN = AC_NODE
-IN = FB_NODE
OUT = AMP_OUT

Feedback network (sets gain around BIAS_BUF):
AMP_OUT --- R5 (Rf) ---+
|
FB_NODE --- R4 (Rg) --- BIAS_BUF


Gain ≈ 1 + (Rf/Rg)

Recommended starting gains:
- **Gain ~6×**: R4=10k, R5=47k  (safer if your source is hot)
- **Gain ~11×**: R4=10k, R5=100k (more boost if source is weak)

### 4) Output to ESP32 ADC with protection / filtering

AMP_OUT --- R6 1k --- ADC_IN ----> Heltec GPIO4 (ADC)

Optional smoothing (helps ADC stability):
ADC_IN --- C3 100nF --- GND


Optional clamp protection (if you’re nervous about “spicy” input levels):

ADC_IN ---|<|--- 3V3 (D1 Schottky, e.g. BAT54)
ADC_IN ---|>|--- GND (D2 Schottky, e.g. BAT54)


---

## Breadboard Wiring Notes (1–30 A–E / F–J split)
- Put the op-amp DIP across the centre gap so each pin sits in a separate row.
- Run a **3V3 rail** and a **GND rail** down the breadboard.
- Keep **BIAS node wiring short** and keep **C1 and the op-amp decoupler** physically close to the op-amp pins.
- Star-ground your audio jack sleeve to the same ground rail as the Heltec.

---

## Power + Decoupling (don’t skip this)
Put these right next to the op-amp power pins:
- **C4 100nF** from op-amp VDD to GND (as close as possible)
- **C5 10uF** bulk cap across 3V3 and GND nearby

---

## Parts List (BOM)

### Core
- 1 × Heltec WiFi LoRa 32 V3 (ESP32-S3)
- 1 × **MCP6002** (dual, DIP-8 preferred)  
  - Alternative: TLV9002 / TLV9062 (dual)

### Input + Bias
- 1 × C2 10uF electrolytic (input coupling)
- 2 × R1,R2 100k (bias divider)
- 1 × C1 100nF ceramic (bias filter)
- 1 × R3 100k (bias feed for AC_NODE)

### Amplifier gain network
Choose ONE gain set:

**Option A (recommended start): Gain ~6×**
- 1 × R4 10k (Rg)
- 1 × R5 47k (Rf)

**Option B: Gain ~11×**
- 1 × R4 10k (Rg)
- 1 × R5 100k (Rf)

### ADC output conditioning
- 1 × R6 1k (series into ADC)
- Optional: 1 × C3 100nF (ADC RC smoothing)

### Protection (optional but nice)
- 2 × BAT54 (Schottky clamp diodes) or similar

### Decoupling
- 1 × C4 100nF (op-amp local decoupler)
- 1 × C5 10uF electrolytic (bulk near op-amp)

### Build bits
- 1 × DIP-8 socket (recommended)
- Breadboard + jumper wires
- Optional: 3.5mm jack breakout

---

## Quick sanity checks (before you power up)
1) BIAS divider midpoint should read ~1.65V (half of 3.3V)
2) BIAS buffer output should also read ~1.65V
3) ADC_IN should sit around ~1.65V when no audio is present
4) With audio applied, ADC_IN should swing around BIAS, not below 0V or above 3.3V

---

## Code reminder
Your sketch already uses:
- `ADC_PIN = 4;`
So wire **ADC_IN → GPIO4**.

---

## Troubleshooting
- If decoding is “always on”: reduce gain (use 47k feedback, or even 22k).
- If it’s deaf: increase gain (100k feedback) or reduce squelch threshold in UI.
- If it’s noisy: add C3 (100nF) at ADC_IN and keep wires short.
