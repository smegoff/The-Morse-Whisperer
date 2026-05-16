#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

APP = Path('/opt/morse-whisperer-pi')
IMG = APP / 'assets' / 'horse_boot_splash.png'
FB = '/dev/fb1' if os.path.exists('/dev/fb1') else '/dev/fb0'
W,H = 320,240

def write(img):
    img = img.convert('RGB').resize((W,H))
    raw=bytearray()
    for r,g,b in img.getdata():
        v=((r&0xF8)<<8)|((g&0xFC)<<3)|(b>>3)
        raw += int(v).to_bytes(2,'little')
    with open(FB,'wb',buffering=0) as f: f.write(raw)

def main():
    try:
        base = Image.open(IMG).convert('RGB').resize((W,H)) if IMG.exists() else Image.new('RGB',(W,H),'black')
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
        start=time.time(); duration=4.0
        while time.time()-start < duration:
            img=base.copy(); d=ImageDraw.Draw(img)
            t=time.time()-start; x=int(24 + (W-48)*(t/duration))
            d.rounded_rectangle((34,218,286,225), radius=4, outline=(60,200,220), width=1)
            d.rounded_rectangle((36,220,x,223), radius=3, fill=(66,248,255))
            d.text((108,204),'BOOTING',font=font,fill=(255,176,46))
            write(img); time.sleep(0.08)
    except Exception:
        sys.exit(0)

if __name__ == '__main__': main()
