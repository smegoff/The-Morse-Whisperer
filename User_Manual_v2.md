# The Morse Whisperer — User Manual

This is a Heltec WiFi LoRa 32 **V3** (ESP32‑S3) CW “tone → text” decoder.

It listens to an **audio tone** (typically ~400–1000 Hz CW sidetone), detects key up/down timing, and decodes Morse into:

- **RAW** text (what was sent)
- **EXPANDED** text (common abbreviations expanded, optional)

It also hosts its own Wi‑Fi AP and a small mobile‑friendly Web UI.

> **Important:** The ESP32 ADC is **0–3.3V only**. This project biases audio around ~1.65V so the ADC never sees negative voltage.

---

## What you need (hardware)

### Core
- Heltec WiFi LoRa 32 V3

### Audio front‑end (this repo’s OP07CP version)
- OP07CP op‑amp (DIP‑8 preferred) + optional DIP‑8 socket
- R1 100k, R2 100k (mid‑rail divider)
- C2 100n (bias node stabiliser)
- C1 10µF (audio coupling cap)
- Rg 10k, Rf 100k (non‑inverting gain ≈ 11×)
- R3 1k (series protection into ADC)
- C3 100n (optional ADC low‑pass)
- C4 100n + C5 10µF (op‑amp supply decoupling)

### Input connector
- 3.5mm jack breakout (recommended) or just fly‑leads from your radio’s audio output

---

## Wiring overview

### Heltec connections (as used by the sketch)
- **3V3** → op‑amp V+
- **GND** → op‑amp GND (and audio ground)
- **GPIO4 / ADC** → op‑amp output (through **R3 1k**)

If you change the ADC pin in firmware, update `ADC_PIN` in the sketch.

---

## Schematics + diagrams (for GitHub)

- **Schematic (OP07CP front‑end):** `docs/schematic_op07.png` (and `.svg`)
- **Breadboard layout (OP07CP front‑end):** `docs/breadboard_layout_op07.png` (and `.svg`)

These are intended for README / GitHub viewing.

---

## Build steps (breadboard)

1. Place the **Heltec V3** across the breadboard centre gap (straddling the split).
2. Place the **OP07CP (DIP‑8)** across the centre gap near the bottom.
3. Run **3.3V** and **GND** from the Heltec to your breadboard rails.
4. Build the **bias node** (R1/R2 + C2).
5. Wire the op‑amp as **non‑inverting** with Rg/Rf.
6. Feed op‑amp output through **R3 1k** into **GPIO4 (ADC)**.
7. Add **C4 100n** and **C5 10µF** right beside the op‑amp between 3V3 and GND.
8. Connect your radio audio:
   - Audio signal → **C1** → biased non‑inverting input
   - Audio ground → common **GND**

---

## Firmware usage

### Controls (PRG button)
- **Hold ~1s:** open menu / select menu item (depends on screen)
- **Hold ~2s:** “panic” back to main screen
- **Short press:** next item / increment value (depends on screen)

### First run checklist
1. Power up.
2. Connect to Wi‑Fi AP **“The Horse Whisperer”** (password `cwdecode123`).
3. Browse to the IP shown on screen (usually `192.168.4.1`).
4. Hit **Calibrate** while sending a steady tone / CQ.
5. If decode is flaky:
   - raise **Sensitivity** a bit
   - lower **Squelch** a bit

---

## Web UI

Open the root page `/` and you’ll get:

- Current mode (RX/TRAIN)
- Tone, WPM estimate, SNR
- LoRa state
- RAW + EXPANDED outputs
- Controls for training/calibration/clear, and live sliders for sensitivity + squelch

---

## Calibration tips (the bit everyone forgets)

- Calibration finds the strongest tone between ~400–1000 Hz.
- Do it while sending a **steady** tone (your sidetone, or a clean CW carrier audio output).
- If you switch radios or filters, recalibrate.

---

## Troubleshooting

### “Nothing decodes”
- Confirm your radio audio is **actually present** (headphones, scope, phone recorder, whatever).
- Check:
  - common GND between radio and Heltec/op‑amp
  - ADC pin is correct (`GPIO4` in firmware)
  - bias node is ~1.65V (multimeter)

### “It’s super noisy / random characters”
- Add the optional **C3 100n** at ADC.
- Keep wires short (breadboards are antenna farms).
- Increase squelch slightly, then calibrate again.

### “Clipping / harsh decode”
- Reduce gain (try Rf = 47k or 22k).
- Add an input pot (10k) as a level trim.

### “OP07CP on 3.3V is weird”
It’s not a rail‑to‑rail op‑amp. That’s fine if you keep the signal small (hundreds of mV around bias).
If you want maximum headroom, use a modern rail‑to‑rail part (e.g., MCP6002 / TLV9002).

---

## Files in this pack

- `morse_whisperer_op07_frontend.kicad_sch` — KiCad 9 schematic (OP07CP version)
- `docs/schematic_op07.svg/png` — clean GitHub diagram
- `docs/breadboard_layout_op07.svg/png` — breadboard placement diagram
- `docs/README.md` — quick reference

---

## Licence

Use it, remix it, improve it. Just don’t blame the bird if you wire 5V into an ADC pin.
