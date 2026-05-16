from __future__ import annotations

import subprocess
import threading
import time
from collections import deque
from typing import Optional

import numpy as np


class AudioRing:
    def __init__(self, sample_rate: int, seconds: float) -> None:
        self.sample_rate = sample_rate
        self.max_samples = int(sample_rate * seconds)
        self._buf = deque(maxlen=self.max_samples)
        self._lock = threading.RLock()
        self.total_samples = 0
        self.overruns = 0

    def append_i16(self, data: bytes) -> None:
        arr = np.frombuffer(data, dtype="<i2")
        with self._lock:
            self._buf.extend(int(x) for x in arr)
            self.total_samples += len(arr)

    def latest(self, seconds: float) -> np.ndarray:
        n = int(self.sample_rate * seconds)
        with self._lock:
            vals = list(self._buf)[-n:]
        return np.asarray(vals, dtype=np.int16)

    def buffered_seconds(self) -> float:
        with self._lock:
            return len(self._buf) / float(self.sample_rate)


def start_capture(ring: AudioRing, device: str, sample_rate: int, blocksize: int, stop_event: threading.Event):
    cmd = ["arecord", "-q", "-D", device, "-r", str(sample_rate), "-f", "S16_LE", "-c", "1", "-t", "raw"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def reader() -> None:
        bytes_per_read = max(64, int(blocksize) * 2)
        try:
            while not stop_event.is_set():
                data = proc.stdout.read(bytes_per_read) if proc.stdout else b""
                if not data:
                    time.sleep(0.02)
                    if proc.poll() is not None:
                        break
                    continue
                ring.append_i16(data)
        finally:
            try:
                proc.terminate()
            except Exception:
                pass

    thread = threading.Thread(target=reader, name="audio-capture", daemon=True)
    thread.start()
    return proc
