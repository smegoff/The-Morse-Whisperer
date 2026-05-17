from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence

import numpy as np

MORSE_TABLE = {
    ".-":"A", "-...":"B", "-.-.":"C", "-..":"D", ".":"E", "..-.":"F", "--.":"G", "....":"H",
    "..":"I", ".---":"J", "-.-":"K", ".-..":"L", "--":"M", "-.":"N", "---":"O", ".--.":"P",
    "--.-":"Q", ".-.":"R", "...":"S", "-":"T", "..-":"U", "...-":"V", ".--":"W", "-..-":"X",
    "-.--":"Y", "--..":"Z", ".----":"1", "..---":"2", "...--":"3", "....-":"4", ".....":"5",
    "-....":"6", "--...":"7", "---..":"8", "----.":"9", "-----":"0", ".-.-.-":".", "--..--":",",
    "..--..":"?", "-..-.":"/", "-...-":"=", ".-.-.":"+", "...---...":"SOS",
}

@dataclass
class DecodeResult:
    raw: str
    copy: str
    selected_tone_hz: int
    target_tone_hz: int
    tone_mode: str
    winner_ratio: float
    snr_db: float
    confidence: float
    dot_ms: float
    wpm: float
    audio: Dict[str, float | str]
    tone_ranking: List[Dict[str, float]]
    events: List[Dict[str, float | str]]
    marks: int
    spaces: int
    decoded_symbols: int
    failed_symbols: int
    filter_enabled: bool = False
    filter_mode: str = "off"
    filter_low_hz: float = 0.0
    filter_high_hz: float = 0.0
    filter_bandwidth_hz: float = 0.0
    reason: str = "ok"


def _float_audio(samples: np.ndarray) -> np.ndarray:
    arr = np.asarray(samples)
    if arr.ndim > 1:
        arr = arr[:, 0]
    if arr.dtype.kind in "iu":
        arr = arr.astype(np.float32) / 32768.0
    else:
        arr = arr.astype(np.float32)
    arr = arr - float(np.mean(arr))
    return arr


def _metrics(x: np.ndarray) -> Dict[str, float | str]:
    if len(x) == 0:
        return {"rms": 0.0, "peak": 0.0, "clipping_percent": 0.0, "dc_offset": 0.0, "level_status": "IDLE"}
    rms = float(np.sqrt(np.mean(x*x)))
    peak = float(np.max(np.abs(x)))
    clip = float(np.mean(np.abs(x) > 0.98) * 100.0)
    if peak > 0.95 or clip > 0.1:
        status = "CLIP"
    elif rms < 0.003:
        status = "IDLE"
    elif rms < 0.01:
        status = "LOW"
    else:
        status = "OK"
    return {"rms": rms, "peak": peak, "clipping_percent": clip, "dc_offset": 0.0, "level_status": status}


def _filter_settings(config: Dict, sr: int, tone_hz: int) -> tuple[bool, str, float, float, float]:
    enabled = bool(config.get("audio_filter_enabled", True))
    mode = str(config.get("audio_filter_mode", "wide") or "wide").lower()
    nyq = sr / 2.0
    if not enabled or mode == "off":
        return False, "off", 0.0, 0.0, 0.0

    if mode == "narrow":
        bandwidth = float(config.get("audio_filter_narrow_hz", 220))
    elif mode == "custom":
        bandwidth = float(config.get("audio_filter_bandwidth_hz", 300))
    else:
        mode = "wide"
        bandwidth = float(config.get("audio_filter_wide_hz", 500))

    bandwidth = max(80.0, min(float(config.get("audio_filter_max_hz", 1200)), bandwidth))
    half = bandwidth / 2.0
    low = max(40.0, float(tone_hz) - half)
    high = min(nyq - 50.0, float(tone_hz) + half)
    if high <= low:
        return False, "off", 0.0, 0.0, 0.0
    return True, mode, low, high, bandwidth


def _fft_bandpass(x: np.ndarray, sr: int, low_hz: float, high_hz: float, transition_hz: float = 45.0) -> np.ndarray:
    """Small dependency-free FFT band-pass for analysis windows.

    This is not used for audio playback. It simply reduces off-frequency energy before
    the Goertzel envelope and timing detector run. The soft transition avoids hard-bin
    ringing while keeping install dependencies light; no scipy required.
    """
    if len(x) < 32 or high_hz <= low_hz:
        return x
    spectrum = np.fft.rfft(x.astype(np.float32))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / sr)
    mask = np.zeros_like(freqs, dtype=np.float32)
    passband = (freqs >= low_hz) & (freqs <= high_hz)
    mask[passband] = 1.0
    if transition_hz > 0:
        lo = (freqs >= max(0.0, low_hz - transition_hz)) & (freqs < low_hz)
        if np.any(lo):
            mask[lo] = 0.5 - 0.5 * np.cos(np.pi * (freqs[lo] - (low_hz - transition_hz)) / transition_hz)
        hi = (freqs > high_hz) & (freqs <= high_hz + transition_hz)
        if np.any(hi):
            mask[hi] = 0.5 + 0.5 * np.cos(np.pi * (freqs[hi] - high_hz) / transition_hz)
    filtered = np.fft.irfft(spectrum * mask, n=len(x))
    return filtered.astype(np.float32)


def _goertzel_power(block: np.ndarray, sr: int, tone: float) -> float:
    if len(block) == 0:
        return 0.0
    n = len(block)
    k = int(0.5 + (n * tone) / sr)
    w = (2.0 * math.pi * k) / n
    coeff = 2.0 * math.cos(w)
    s0 = s1 = s2 = 0.0
    for sample in block:
        s0 = float(sample) + coeff * s1 - s2
        s2 = s1
        s1 = s0
    return float(s1*s1 + s2*s2 - coeff*s1*s2) / max(n, 1)


def _tone_envelope(x: np.ndarray, sr: int, tone: int, block_n: int, hop_n: int) -> np.ndarray:
    vals = []
    for start in range(0, max(1, len(x) - block_n + 1), hop_n):
        block = x[start:start+block_n]
        if len(block) < block_n:
            break
        vals.append(_goertzel_power(block, sr, tone))
    return np.asarray(vals, dtype=np.float32)


def _events(mask: np.ndarray, hop_ms: float) -> List[Dict[str, float | str]]:
    if len(mask) == 0:
        return []
    out = []
    state = bool(mask[0])
    start = 0
    for i in range(1, len(mask)):
        if bool(mask[i]) != state:
            out.append({"kind": "mark" if state else "space", "ms": (i-start)*hop_ms, "start_ms": start*hop_ms, "end_ms": i*hop_ms})
            start = i
            state = bool(mask[i])
    out.append({"kind": "mark" if state else "space", "ms": (len(mask)-start)*hop_ms, "start_ms": start*hop_ms, "end_ms": len(mask)*hop_ms})
    return out


def _estimate_dot(events: List[Dict[str, float | str]], initial_wpm: float) -> float:
    marks = sorted(float(e["ms"]) for e in events if e["kind"] == "mark" and 15 <= float(e["ms"]) <= 2000)
    if not marks:
        return 1200.0 / max(initial_wpm, 1.0)
    low = marks[:max(3, len(marks)//2)]
    return max(25.0, min(500.0, float(np.median(low))))


def _decode(events: List[Dict[str, float | str]], dot_ms: float, char_gap: float, word_gap: float) -> tuple[str, str, int, int]:
    chars: List[str] = []
    current = ""
    decoded = failed = 0
    for e in events:
        kind = str(e["kind"])
        units = float(e["ms"]) / max(dot_ms, 1.0)
        if kind == "mark":
            current += "." if units < 2.0 else "-"
        elif kind == "space":
            if units < char_gap:
                continue
            if current:
                val = MORSE_TABLE.get(current, "#")
                decoded += val != "#"
                failed += val == "#"
                chars.append(val)
                current = ""
            if units >= word_gap and chars and chars[-1] != " ":
                chars.append(" ")
    if current:
        val = MORSE_TABLE.get(current, "#")
        decoded += val != "#"
        failed += val == "#"
        chars.append(val)
    raw = "".join(chars)
    copy = " ".join(raw.split())
    return raw, copy, decoded, failed


def analyse_samples(samples: np.ndarray, config: Dict) -> DecodeResult:
    sr = int(config.get("sample_rate", 8000))
    x_raw = _float_audio(samples)
    audio = _metrics(x_raw)
    tones: Sequence[int] = config.get("allowed_tones_hz") or [700]
    block_n = max(16, int(sr * float(config.get("window_ms", 12)) / 1000.0))
    hop_n = max(8, int(sr * float(config.get("hop_ms", 8)) / 1000.0))
    hop_ms = hop_n * 1000.0 / sr

    # First pass: tone ranking uses unfiltered audio so full-auto can still find the tone.
    ranking = []
    raw_envs = {}
    for tone in tones:
        env = _tone_envelope(x_raw, sr, int(tone), block_n, hop_n)
        raw_envs[int(tone)] = env
        ranking.append({"tone_hz": int(tone), "score": float(np.percentile(env, 95)) if len(env) else 0.0})
    ranking.sort(key=lambda r: r["score"], reverse=True)
    selected = int(ranking[0]["tone_hz"]) if ranking else int(config.get("target_tone_hz", 700))
    if str(config.get("tone_mode", "session_auto")) in ("fixed", "manual"):
        selected = int(config.get("target_tone_hz", selected))

    filter_enabled, filter_mode, filter_low, filter_high, filter_bw = _filter_settings(config, sr, selected)
    x = _fft_bandpass(x_raw, sr, filter_low, filter_high) if filter_enabled else x_raw
    env = _tone_envelope(x, sr, selected, block_n, hop_n)

    if len(env) == 0:
        return DecodeResult("", "", selected, int(config.get("target_tone_hz", selected)), str(config.get("tone_mode", "session_auto")), 0, 0, 0, 1200/18.75, 18.75, audio, ranking, [], 0, 0, 0, 0, filter_enabled, filter_mode, filter_low, filter_high, filter_bw, "no audio")
    noise = float(np.percentile(env, 35))
    signal = float(np.percentile(env, 92))
    threshold = noise + (signal - noise) * float(config.get("threshold_bias", 0.48))
    mask = env > threshold
    ev = _events(mask, hop_ms)
    ev = [e for e in ev if float(e["ms"]) >= 0.45 * hop_ms]
    dot = _estimate_dot(ev, float(config.get("initial_wpm", 18.75)))
    wpm = 1200.0 / max(dot, 1.0)
    raw, copy, decoded, failed = _decode(ev, dot, float(config.get("char_gap_units", 2.25)), float(config.get("word_gap_units", 6.5)))
    top = ranking[0]["score"] if ranking else 0.0
    second = ranking[1]["score"] if len(ranking) > 1 else max(noise, 1e-12)
    ratio = float(top / max(second, 1e-12))
    snr = float(10.0 * math.log10(max(signal, 1e-12) / max(noise, 1e-12)))
    conf = max(0.0, min(1.0, (snr / 30.0) * min(1.0, ratio / 6.0)))
    return DecodeResult(raw, copy, selected, int(config.get("target_tone_hz", selected)), str(config.get("tone_mode", "session_auto")), ratio, snr, conf, dot, wpm, audio, ranking, ev[-int(config.get("max_events_in_snapshot", 160)):], sum(e["kind"]=="mark" for e in ev), sum(e["kind"]=="space" for e in ev), decoded, failed, filter_enabled, filter_mode, filter_low, filter_high, filter_bw, "ok")
