# Troubleshooting

## 1) Task watchdog resets (WDT)
Symptoms:
- "task_wdt: IDLE0 did not reset watchdog"
- reboots shortly after boot

Causes:
- A high-priority task on CPU0 starving IDLE0
- Busy-wait loops that never yield

Fixes:
- Ensure sampler task yields regularly
- Prefer running sampler on CPU1 if CPU0 is sensitive
- Lower sampler priority (1 is usually fine)

## 2) Decodes garbage / always-on tone
- Input is clipping (not biased to mid-rail)
- Sensitivity too high
- Tone frequency mismatch

Fix:
- Verify analogue front-end (bias + AC couple)
- Run Calibrate
- Reduce sensitivity
- Increase squelch slightly

## 3) Nothing decodes
- Squelch too high
- Input too low
- Wrong ADC pin

Fix:
- Lower squelch threshold
- Increase input gain
- Confirm ADC_PIN is valid for Heltec V3 ADC

## 4) Calibration locks to 400 Hz constantly
Usually means:
- there's no strong tone in the scanned band
- or the input signal is dominated by low-frequency junk / aliasing

Fix:
- Ensure the CW sidetone is present and within 400–1000Hz
- Improve input conditioning (filtering, level, bias)
- Try manual Tone set near your sidetone (eg 700Hz) then recalibrate
