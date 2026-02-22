# Breadboard build notes

## Keep it tidy
- Keep the bias resistors, bias cap, and op-amp close together.
- Keep the ADC wire short.
- Keep audio wires short and twisted if possible (signal + ground).

## Common gotchas
- No shared ground between radio audio source and Heltec → nothing works.
- Feeding negative audio into ADC without bias → chaos.
- Long jumper spaghetti → noise & false triggering.

## Quick functional test
1) Power the Heltec and op-amp stage.
2) Measure OP07 output idle voltage (Pin 6) ~ 1.65V.
3) Inject tone (e.g., 700 Hz) and verify output wiggles around ~1.65V.
4) Connect to GPIO 4 and test decode.
