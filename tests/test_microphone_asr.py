import unittest
from pathlib import Path
import tempfile

import numpy as np

from agent_voice.asr.microphone import collect_fixed_duration
from agent_voice.app import _prepare_mic_asr_wav_path
from agent_voice.ui.qt_widget import _format_voice_status


class MicrophoneAsrTest(unittest.TestCase):
    def test_collects_expected_number_of_frames(self):
        frames = [np.ones(4, dtype=np.float32) * index for index in range(3)]

        samples = collect_fixed_duration(lambda: frames.pop(0), frame_count=3)

        np.testing.assert_array_equal(samples, np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2], dtype=np.float32))

    def test_returns_empty_samples_when_no_frames_are_requested(self):
        samples = collect_fixed_duration(lambda: np.ones(4, dtype=np.float32), frame_count=0)

        self.assertEqual(samples.size, 0)

    def test_formats_microphone_asr_result_for_widget(self):
        text = _format_voice_status({"event": "mic_asr_result", "asr_text": "小猪小猪", "asr_elapsed_ms": 1200})

        self.assertEqual(text, "麦克风ASR：小猪小猪\n耗时：1200 ms")

    def test_formats_empty_microphone_asr_for_widget(self):
        text = _format_voice_status({"event": "mic_asr_empty", "message": "未识别到文字"})

        self.assertEqual(text, "麦克风ASR：未识别到文字")

    def test_prepares_requested_microphone_asr_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "captures" / "last.wav"

            wav_path, keep_wav = _prepare_mic_asr_wav_path(str(output_path))

            self.assertEqual(wav_path, output_path)
            self.assertTrue(keep_wav)
            self.assertTrue(output_path.parent.exists())


if __name__ == "__main__":
    unittest.main()
