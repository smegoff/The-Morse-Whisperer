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
- OpenAI-backed listening analysis and reply drafting via `/api/cq/plan`.
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
  "cq_ai_provider": "openai",
  "cq_ai_model": "gpt-4.1-mini",
  "cq_allow_transmit": false
}
```

`cq_allow_transmit` is forced false by the CQ API. It is present as an explicit
future guardrail, not as an active feature.

OpenAI uses the existing service environment file:

```text
/etc/morse-whisperer/ai.env
```

Set `OPENAI_API_KEY` there for OpenAI-backed planning. If the key is absent or
the provider fails, CQ planning falls back to the local rules engine and reports
a warning.

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

## Planned Phases

1. Read-only CAT and busy-frequency status.
2. OpenAI-assisted receive-side listening, callsign extraction, intent
   detection, and draft reply planning.
3. Local QSO/session log skeleton.
4. Human-approved CW reply drafting.
5. Guarded transmit path with explicit arm/disarm, band allowlist, max TX time,
   PTT watchdog, and stop-now control.
6. QRZ logbook sync from complete local records.

The transmit path should not be added until the listen-only path can reliably
show when a frequency is occupied and what station, if any, is being copied.
