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
dtoverlay=pitft28-resistive,rotate=90,speed=32000000,fps=20
```

Full KMS should be disabled for this SPI framebuffer setup:

```text
#dtoverlay=vc4-kms-v3d
```

The app uses `/dev/fb1` first and falls back to `/dev/fb0`.
