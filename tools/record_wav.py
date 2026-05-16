#!/usr/bin/env python3
import argparse, subprocess
p=argparse.ArgumentParser(); p.add_argument('output'); p.add_argument('--device',default='plughw:2,0'); p.add_argument('--seconds',type=int,default=10); a=p.parse_args()
subprocess.check_call(['arecord','-D',a.device,'-r','8000','-f','S16_LE','-c','1','-d',str(a.seconds),a.output])
