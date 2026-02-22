**actual circuit you need** for The Morse Whisperer, assuming we are feeding **audio into the Heltec WiFi LoRa 32 V3 ADC (GPIO4)**.

### 1) Audio input conditioning (recommended “just works” version)

**Goal:** take headphone/line audio (or speaker-level via attenuator), centre it at mid-rail, and protect the ESP32 ADC.

**Parts**

* 1 × **10 µF** electrolytic (coupling cap)
* 2 × **100 kΩ** resistors (bias divider)
* 1 × **1 kΩ** resistor (series protection)
* 1 × **100 nF** capacitor (bias smoothing)
* 2 × **Schottky diodes** (BAT54S or 2× BAT54 / 1N5819) *optional but good*
* A **pot** optional (10 k–50 k) if you want input level control

**Wiring (text schematic)**

* Make a **bias midpoint** for the ADC:

  * **3V3 → 100k → (BIAS node) → 100k → GND**
  * **BIAS node → 100nF → GND** (stabilise the midpoint)

* Feed audio in through a **coupling capacitor**:

  * **Audio signal → 10µF cap → 1k resistor → ADC pin (GPIO4)**
  * And connect **ADC pin** to the **BIAS node** (so ADC rides at mid-rail)

So it’s essentially:

**Audio → [10µF] → [1k] → ADC(GPIO4)**
and **ADC(GPIO4)** is also tied to **BIAS (made by 100k/100k + 100nF)**.

**Ground:** Audio ground must connect to Heltec **GND**.

**Optional clamp protection (nice insurance):**

* Clamp ADC to rails using Schottkys:

  * **ADC → diode → 3V3** (conducts if ADC goes above 3V3)
  * **GND → diode → ADC** (conducts if ADC goes below 0V)

(Orientation matters: you want them to conduct only when you exceed rails.)

---

### 2) If you’re coming from a speaker output (hotter signal)

Speaker outputs can be way too spicy 🌶️ for ADC.

Add a simple attenuator before the coupling cap:

* **Audio signal → 10k series → node → (to coupling cap)**
* **node → 10k to GND**

That’s roughly a **2:1** drop. If it’s still too hot, make it **47k series / 10k to GND**.

---

### 3) If you’re using a mic / electret capsule

Different beast: needs bias and an amp. For an easy life:

* Use a **MAX9814** (auto-gain mic amp board) or similar.
* Then still use the **same coupling cap + mid-bias** into the ADC.

---

### 4) OLED + power bits (quick sanity)

* OLED is I2C: **SDA GPIO17, SCL GPIO18**, reset GPIO21 (as in your code)
* VEXT enable pin in your code: GPIO36 (varies by revision; yours seems OK since OLED works)

---

### Quick “don’t blow it up” rules

* ADC must stay **0–3.3V**.
* Don’t feed AC audio straight in without the **bias midpoint**.
* Always share **ground** between audio source and Heltec.

If you tell me what your audio source actually is (radio headphone out, line-out, speaker, discriminator, etc.), I can give you the best resistor values so it lands right in the sweet spot without clipping.
