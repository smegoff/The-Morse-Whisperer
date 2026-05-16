#!/usr/bin/env python3
import argparse, wave, json, numpy as np
from morse_whisperer.config import load_config
from morse_whisperer.dsp import analyse_samples
p=argparse.ArgumentParser(); p.add_argument('wav'); a=p.parse_args()
with wave.open(a.wav,'rb') as w: data=w.readframes(w.getnframes())
s=np.frombuffer(data,dtype='<i2')
r=analyse_samples(s, load_config())
print(json.dumps(r.__dict__, indent=2, default=str))
