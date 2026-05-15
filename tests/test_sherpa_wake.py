import unittest
from pathlib import Path

import numpy as np

from agent_voice.wake.sherpa_onnx_engine import SherpaOnnxWakeDetector


class FakeStream:
    def __init__(self):
        self.accepted = []

    def accept_waveform(self, sample_rate, samples):
        self.accepted.append((sample_rate, samples.tolist()))


class FakeSpotter:
    def __init__(self, results):
        self.results = list(results)
        self.stream = FakeStream()
        self.decoded = 0
        self.reset_count = 0

    def create_stream(self):
        return self.stream

    def is_ready(self, stream):
        return self.decoded == 0

    def decode_stream(self, stream):
        self.decoded += 1

    def get_result(self, stream):
        if self.results:
            return self.results.pop(0)
        return ""

    def reset_stream(self, stream):
        self.reset_count += 1


class SherpaOnnxWakeDetectorTest(unittest.TestCase):
    def test_returns_keyword_when_spotter_detects_it(self):
        spotter = FakeSpotter(["小图小图"])
        detector = SherpaOnnxWakeDetector(
            model_dir=Path("models/wake/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"),
            keywords_file=Path("models/wake/keywords.txt"),
            spotter_factory=lambda **kwargs: spotter,
            cooldown_ms=0,
        )

        result = detector.accept_samples(np.array([0.1, 0.2], dtype=np.float32), sample_rate=16000, now_ms=1000)

        self.assertEqual(result, "小图小图")
        self.assertEqual(spotter.stream.accepted[0][0], 16000)
        self.assertEqual(spotter.decoded, 1)
        self.assertEqual(spotter.reset_count, 1)

    def test_cooldown_suppresses_repeated_detection(self):
        spotter = FakeSpotter(["小图小图", "小图小图"])
        detector = SherpaOnnxWakeDetector(
            model_dir=Path("models/wake/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"),
            keywords_file=Path("models/wake/keywords.txt"),
            spotter_factory=lambda **kwargs: spotter,
            cooldown_ms=1500,
        )

        first = detector.accept_samples(np.array([0.1], dtype=np.float32), sample_rate=16000, now_ms=1000)
        second = detector.accept_samples(np.array([0.1], dtype=np.float32), sample_rate=16000, now_ms=1200)

        self.assertEqual(first, "小图小图")
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()
