#!/usr/bin/env python3
import subprocess
for cmd in (['arecord','-l'], ['aplay','-l']):
    print('\n===', ' '.join(cmd), '===')
    subprocess.run(cmd, check=False)
