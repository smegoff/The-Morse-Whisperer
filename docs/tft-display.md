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
dtoverlay=tft9341,rotate=90,speed=32000000,fps=20
```

This overlay drives the ILI9340 framebuffer on SPI CS0 and the ADS7846
resistive touchscreen on SPI CS1. On the verified appliance the touch input
appears as:

```text
N: Name="ADS7846 Touchscreen"
H: Handlers=mouse0 event1
```

Full KMS should be disabled for this SPI framebuffer setup:

```text
#dtoverlay=vc4-kms-v3d
```

The app uses `/dev/fb1` first and falls back to `/dev/fb0`.

The older `pitft28-resistive` overlay brings up the display on some builds, but
it probes an STMPE touchscreen controller. On this XC9022/GoodTFT unit that
results in `stmpe-spi spi0.1: unknown chip id: 0x0` and no touch input device.
