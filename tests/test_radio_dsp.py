from __future__ import annotations

import unittest

import numpy as np

from morse_whisperer.dsp import analyse_samples


MORSE = {
    "C": "-.-.", "Q": "--.-", "D": "-..", "E": ".", "Z": "--..",
    "L": ".-..", "1": ".----", "S": "...", "X": "-..-", "G": "--.",
    "K": "-.-",
}


def synthetic_cw(text: str, tone_hz: int, amplitude: float = 0.10, noise: float = 0.0) -> np.ndarray:
    sample_rate = 8000
    dot = 0.064
    chunks = [np.zeros(int(sample_rate * 0.25), dtype=np.float32)]

    def silence(units: float) -> None:
        chunks.append(np.zeros(int(sample_rate * dot * units), dtype=np.float32))

    def mark(units: float) -> None:
        count = int(sample_rate * dot * units)
        t = np.arange(count, dtype=np.float32) / sample_rate
        envelope = np.ones(count, dtype=np.float32)
        fade = min(int(sample_rate * 0.004), count // 2)
        if fade:
            envelope[:fade] = np.linspace(0, 1, fade, dtype=np.float32)
            envelope[-fade:] = np.linspace(1, 0, fade, dtype=np.float32)
        chunks.append(amplitude * envelope * np.sin(2 * np.pi * tone_hz * t))

    words = text.split()
    for word_index, word in enumerate(words):
        if word_index:
            silence(7)
        for char_index, char in enumerate(word):
            if char_index:
                silence(3)
            for element_index, element in enumerate(MORSE[char]):
                if element_index:
                    silence(1)
                mark(1 if element == "." else 3)
    silence(7)

    signal = np.concatenate(chunks)
    if noise:
        signal = signal + np.random.default_rng(7).normal(0, noise, signal.size).astype(np.float32)
    return signal.astype(np.float32)


def radio_config() -> dict:
    return {
        "sample_rate": 8000,
        "tone_mode": "auto",
        "target_tone_hz": 650,
        "allowed_tones_hz": list(range(400, 1001, 50)),
        "radio_keyed_tone_scoring": True,
        "radio_tone_score_window_ms": 80,
        "radio_tone_score_hop_ms": 10,
        "radio_tone_score_max_sec": 2.5,
        "radio_fine_tone_search": True,
        "radio_tone_fine_step_hz": 5,
        "radio_tone_fine_span_hz": 25,
        "radio_tone_coarse_candidates": 2,
        "radio_tone_competitor_separation_hz": 25,
        "radio_tone_min_hz": 350,
        "radio_tone_max_hz": 1100,
        "audio_filter_enabled": True,
        "audio_filter_mode": "narrow",
        "audio_filter_narrow_hz": 260,
        "initial_wpm": 18.75,
        "threshold_bias": 0.5,
        "window_ms": 12,
        "hop_ms": 8,
        "char_gap_units": 2.7,
        "word_gap_units": 5.6,
        "adaptive_word_gap_enabled": True,
        "adaptive_word_gap_min_units": 5.2,
        "adaptive_word_gap_max_units": 6.8,
        "min_element_fraction": 0.45,
        "squelch_snr": 3.5,
    }


class RadioToneTests(unittest.TestCase):
    def test_fine_search_finds_off_grid_cw_beside_stronger_carrier(self) -> None:
        samples = synthetic_cw("CQ DE ZL1SXG K", 675, amplitude=0.10, noise=0.003)
        t = np.arange(samples.size, dtype=np.float32) / 8000.0
        samples += 0.16 * np.sin(2 * np.pi * 750 * t)

        result = analyse_samples(samples, radio_config())

        self.assertLessEqual(abs(result.selected_tone_hz - 675), 5)
        self.assertEqual(result.copy, "CQ DE ZL1SXG K")
        self.assertGreater(result.envelope_contrast, 0.2)

    def test_weak_keyed_signal_retains_envelope_contrast(self) -> None:
        samples = synthetic_cw("CQ DE ZL1SXG K", 685, amplitude=0.025, noise=0.004)
        result = analyse_samples(samples, radio_config())

        self.assertLessEqual(abs(result.selected_tone_hz - 685), 5)
        self.assertGreater(result.envelope_contrast, 0.3)
        self.assertGreater(result.decoded_symbols, 5)

    def test_clean_style_config_keeps_legacy_power_selection(self) -> None:
        samples = synthetic_cw("CQ DE ZL1SXG K", 675, amplitude=0.10, noise=0.003)
        t = np.arange(samples.size, dtype=np.float32) / 8000.0
        samples += 0.16 * np.sin(2 * np.pi * 750 * t)
        config = radio_config()
        config["radio_keyed_tone_scoring"] = False
        config["radio_fine_tone_search"] = False

        result = analyse_samples(samples, config)

        self.assertEqual(result.selected_tone_hz, 750)


if __name__ == "__main__":
    unittest.main()
