# Web UI

Open the web UI at:

```text
http://<pi-ip>:8080
```

Tabs:

- **Settings**: decoder tone mode, target tone, WPM hint, input level, TFT brightness, idle splash, output device.
- **CW Generator / Trainer**: enter text, set tone/WPM/volume, and play CW through the USB output.
- **Network Setup**: view IP status, scan Wi-Fi, connect to a network.
- **CQ Rag Chew**: listen-only assisted operating foundation, including callsign,
  CAT read-only setup, and busy-frequency status.

The top of the page shows stable COPY, RAW, tone lock, signal quality, and operator controls.

## Security boundary

The UI has no authentication and includes state-changing controls for decoder
settings, Wi-Fi, audio playback, CQ Rag Chew status setup, and service profile changes. Keep the
appliance on a trusted LAN and do not expose port 8080 to the internet.
