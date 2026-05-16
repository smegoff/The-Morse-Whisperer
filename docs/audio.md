# Audio Setup

The known-good USB audio device appears as both capture and playback card 2:

```text
arecord -l
aplay -l
```

Known-good config:

```text
audio_device: plughw:2,0
audio_output_device: plughw:2,0
```

Test playback:

```bash
speaker-test -D plughw:2,0 -t sine -f 700 -c 1 -l 1
```

The CW trainer uses the configured playback device. Live audio monitor/pass-through is separate from trainer playback and is not required for decoding.
