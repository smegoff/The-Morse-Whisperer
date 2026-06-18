# Web UI

Open the web UI at:

```text
http://<pi-ip>:8080
```

Apps:

- **Morse Whisperer** at `/`: live CW decoder, copy display, station notes,
  decoder settings, trainer, and network setup.
- **CQ Rag Chew** at `/cq`: listen-only assisted operating foundation,
  including callsign, CAT read-only setup, busy-frequency status, and
  provider-backed reply planning.

The top of each app has a small app switcher.

Morse Whisperer tabs:

- **Settings**: decoder tone mode, target tone, WPM hint, input level, TFT brightness, idle splash, output device.
- **CW Generator / Trainer**: enter text, set tone/WPM/volume, and play CW through the USB output.
- **Network Setup**: view IP status, scan Wi-Fi, connect to a network.
- **AI provider keys**: paste Gemini, Groq, OpenRouter, or OpenAI API keys.
  Stored keys are masked in the UI and written to `/etc/morse-whisperer/ai.env`.

The Morse Whisperer app shows stable COPY, RAW, tone lock, signal quality, and operator controls.

## Security boundary

The UI has no authentication and includes state-changing controls for decoder
settings, Wi-Fi, audio playback, CQ Rag Chew status setup, and service profile changes. Keep the
appliance on a trusted LAN and do not expose port 8080 to the internet.
