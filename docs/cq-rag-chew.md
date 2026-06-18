# CQ Rag Chew

CQ Rag Chew is the planned second application for the Morse Whisperer appliance.
Its goal is assisted amateur-radio operating: find clear CW frequencies, call or
answer CQ, help manage a QSO, and eventually log complete contacts.

## Current milestone

The first implementation is listen-only foundation work:

- Standalone web app at `/cq`, with an app switcher back to the decoder.
- `/api/cq/status` JSON endpoint.
- `/api/cq/settings` JSON endpoint for CQ app settings.
- Read-only CAT status probing through Hamlib `rigctl` when enabled.
- Audio/decode based busy-frequency judgement.
- Receive status for any audible activity, not only CQ calls.
- Provider-backed listening analysis and reply drafting via `/api/cq/plan`.
- Press-to-transcribe voice receive audio via `/api/cq/voice/transcribe`.
- Web waterfall display fed by `/api/waterfall` from recent audio.
- Explicit transmit-disabled safety boundary.

No PTT, frequency changing, automatic CQ calling, or QRZ upload is implemented
in this milestone.

## Configuration

CQ settings live in `config.json` and are preserved by profile switching:

```json
{
  "cq_enabled": false,
  "cq_callsign": "ZL1SXG",
  "cq_cat_enabled": false,
  "cq_cat_backend": "rigctl",
  "cq_cat_model": "3073",
  "cq_cat_device": "/dev/ttyUSB0",
  "cq_cat_baud": 19200,
  "cq_band_allowlist": "40m,20m,15m,10m",
  "cq_busy_rms_threshold": 0.006,
  "cq_busy_snr_threshold_db": 6.0,
  "cq_ai_enabled": true,
  "cq_ai_provider": "gemini",
  "cq_ai_model": "gemini-2.5-flash-lite",
  "cq_allow_transmit": false
}
```

`cq_allow_transmit` is forced false by the CQ API. It is present as an explicit
future guardrail, not as an active feature.

External AI provider keys can be saved from the web UI. In CQ Rag Chew, choose
the provider, paste the key into **Provider API key**, and press **Save API key
& restart**.

Under the hood, keys are stored in the service environment file:

```text
/etc/morse-whisperer/ai.env
```

Set the key for the selected provider there:

```text
GEMINI_API_KEY=...
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
OPENAI_API_KEY=...
```

The installer creates this file as `root:morsewhisperer` with mode `0660` so
the web service can update only this env file. Supported `cq_ai_provider`
values are `local`, `gemini`, `groq`, `openrouter`, and `openai`. If the key is
absent or the provider fails, CQ planning falls back to the local rules engine
and reports a warning.

## Busy-Frequency Judgement

The current channel state is advisory. It reports `busy`, `clear`, or
`unknown` from the live decoder snapshot:

- decoded copy present
- decoder squelch state
- recent keyed activity
- audio RMS level
- SNR
- audio level status

Treat this as a bench-test aid until the radio, audio interface, and CAT path
are proven together.

## Listening First

CQ Rag Chew does not wait only for a decoded `CQ`. It now reports a receive
state from the live audio and decoder:

- `quiet`: no useful activity seen
- `audible`: audio activity is present but no usable text is decoded yet
- `candidate`: partial/candidate decoded text is available
- `decoded`: stable decoded copy is available

The `/api/cq/plan` endpoint uses whatever is currently heard, including
candidate or non-CQ copy, and asks the AI/local planner to interpret it before
suggesting any next action.

## QRM, QRN, and Low Modulation

The receive status also reports likely reasons why audio is audible but not
copyable:

- `low_modulation`: audio is present but too low for reliable copy.
- `possible_qrn`: short static/impulse spikes are dominating the audio.
- `possible_qrm`: competing tones are close enough in strength to confuse tone
  selection.
- `overdriven_audio`: clipping or excessive input level.
- `weak_or_noisy_signal`: audible but low-SNR copy.
- `unkeyed_or_flat_audio`: audio is present but not clearly keyed CW.
- `messy_copy`: candidate copy exists but has many failed symbols.

These diagnostics are advisory. Use them to tune input level, receiver audio,
filter width, and operating frequency before adding any transmit behaviour.

## Waterfall

The `/cq` app includes a lightweight audio waterfall. It renders recent audio
from roughly 250-2200 Hz, which is enough to see CW side tones, obvious QRM,
wideband noise, and level changes through the DE-19/audio interface.

The JSON source is:

```text
/api/waterfall?seconds=3&rows=72&min_hz=250&max_hz=2200
```

## Voice Transcription

The `/cq` app has a **Transcribe voice** button. It captures the most recent
receive audio from the same audio ring used by the decoder, packages it as a
mono WAV file, and asks Gemini to transcribe any speech it can hear:

```text
POST /api/cq/voice/transcribe
```

If Gemini is unavailable or the API key is rejected, the appliance falls back to
local PocketSphinx when installed. PocketSphinx is fully offline and useful as a
basic proof path, but it is less accurate than Gemini on noisy SSB/radio audio.

This is a listen-only, press-to-transcribe feature. It is not a real-time speech
stream yet. Google documents Gemini audio understanding as suitable for
transcription, but not real-time transcription; the future streaming path should
use a dedicated streaming STT engine or Gemini Live once the listen-only flow is
proven.

## Planned Phases

1. Read-only CAT and busy-frequency status.
2. AI-assisted receive-side listening, callsign extraction, intent
   detection, and draft reply planning.
3. Local QSO/session log skeleton.
4. Human-approved CW reply drafting.
5. Guarded transmit path with explicit arm/disarm, band allowlist, max TX time,
   PTT watchdog, and stop-now control.
6. QRZ logbook sync from complete local records.

The transmit path should not be added until the listen-only path can reliably
show when a frequency is occupied and what station, if any, is being copied.
