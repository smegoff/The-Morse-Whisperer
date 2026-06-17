# TFT Display

Known-good framebuffer output:

```text
/sys/class/graphics/fb1/name: fb_ili9340
/sys/class/graphics/fb1/virtual_size: 320,240
/sys/class/graphics/fb1/bits_per_pixel: 16
```

Known-good boot overlay:

```text
dtparam=spi=on
dtoverlay=fbtft,spi0-0,ili9340,dc_pin=25,rotate=90,speed=32000000,fps=20
dtoverlay=ads7846,cs=1,penirq=24,penirq_pull=2,speed=2000000,xohms=60,pmax=255
```

The display uses ILI9340 on SPI CS0 with LCD DC on GPIO25. The resistive touch
controller uses ADS7846/XPT2046 on SPI CS1 with PENIRQ on GPIO24. On the
verified appliance the touch input appears as:

```text
N: Name="ADS7846 Touchscreen"
H: Handlers=mouse0 event1
```

Full KMS should be disabled for this SPI framebuffer setup:

```text
#dtoverlay=vc4-kms-v3d
```

The app uses `/dev/fb1` first and falls back to `/dev/fb0`.

The older `pitft28-resistive` overlay brings up the display on this unit, but
it probes an STMPE touchscreen controller. That results in
`stmpe-spi spi0.1: unknown chip id: 0x0` and no touch input device.

The `tft9341` overlay brings up ADS7846 touch, but it assumes a different LCD
DC/reset wiring and leaves this panel white. Use the split `fbtft` + `ads7846`
configuration above.
