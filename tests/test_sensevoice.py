import unittest
from pathlib import Path

from agent_voice.asr.sensevoice import SenseVoiceAsr


class FakeAutoModel:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return self.output


class SenseVoiceAsrTest(unittest.TestCase):
    def test_transcribes_audio_file_with_local_model(self):
        fake_model = FakeAutoModel([{"text": "<|zh|><|NEUTRAL|><|Speech|>调取患者一二三四五六"}])
        engine = SenseVoiceAsr(
            model_dir="models/asr/SenseVoiceSmall",
            device="cpu",
            model_factory=lambda **kwargs: fake_model,
        )

        result = engine.transcribe_file(Path("sample.wav"))

        self.assertEqual(result.text, "调取患者一二三四五六")
        self.assertEqual(result.confidence, 1.0)
        self.assertGreaterEqual(result.elapsed_ms, 0)
        self.assertEqual(fake_model.calls[0]["input"], "sample.wav")
        self.assertEqual(fake_model.calls[0]["batch_size_s"], 60)

    def test_raises_when_model_returns_no_text(self):
        engine = SenseVoiceAsr(
            model_dir="models/asr/SenseVoiceSmall",
            device="cpu",
            model_factory=lambda **kwargs: FakeAutoModel([{"text": "   "}]),
        )

        with self.assertRaises(ValueError):
            engine.transcribe_file("sample.wav")


if __name__ == "__main__":
    unittest.main()
