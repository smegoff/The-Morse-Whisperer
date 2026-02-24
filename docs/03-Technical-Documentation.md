# Technical Documentation

## Architecture overview
The firmware runs two main loops:

1) **Sampler task** (FreeRTOS task)
- Samples ADC at `SAMPLE_RATE` into blocks of `BLOCK_N` samples
- Pushes blocks into a ring buffer queue
- Must yield often enough to avoid starving IDLE tasks (WDT safety)

2) **Main loop**
- Pops blocks from the ring buffer
- Computes Goertzel magnitude
- Updates detector envelopes and hysteresis thresholds
- Applies squelch gate
- Converts on/off transitions into dot/dash symbols and gaps
- Updates OLED and Web UI

## Sampling strategy
- Uses microsecond scheduling (`micros()`) to target 8 kHz.
- Ring buffer allows processing jitter without dropping samples.
- Sampler yields at safe points to keep RTOS and watchdog happy.

## Tone detection (Goertzel)
- Goertzel is efficient for detecting energy at a single target frequency.
- `computeGoertzelForFreq()` precomputes sin/cos and coeff.
- Magnitude is derived from the final filter states.

## Detector model
- `detectLevel` is an EMA of Goertzel magnitudes
- `noiseFloor` tracks baseline energy slowly
- `signalFloor` tracks stronger energy slowly
- Hysteresis thresholds:
  - `thrOn` to enter tone-present
  - `thrOff` to exit tone-present
- Sensitivity scales these fractions.

## SNR and squelch
- `snrNow ~ detectLevel / noiseFloor`
- `snrEma` smooths `snrNow`
- Squelch opens only when `snrEma >= squelchSNR`

## Morse timing
- Transitions are timed using `millis()`.
- Tone ON duration → MARK length
- Tone OFF duration → SPACE length
- Adaptive dot:
  - collects recent MARK durations
  - estimates a dot candidate (lower quartile-ish)
  - smooths with EMA to avoid jitter

## Training strategies
### Manual “AAAAAAAAAA” lock-in
- Watches decoded output stream.
- Requires a run of 10 consecutive `A` decoded.
- When achieved: locks training off and leaves decoder running.

### Auto training
- Uses stability heuristics (eg. consistent dot estimate, stable SNR, low error-like behaviour).
- Stops actively adjusting once stable.
- Can re-engage if conditions drift.

## Concurrency notes
- Ring buffer push/pop uses a critical section (portMUX).
- Avoid long critical sections.
- Keep OLED/UI updates non-blocking.

## Performance notes
- ADC timing accuracy depends on core speed and WiFi interference.
- Ring buffer depth can be tuned (`AUDIO_Q_BLOCKS`) to balance latency vs robustness.
