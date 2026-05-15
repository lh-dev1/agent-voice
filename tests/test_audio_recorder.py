import unittest

import numpy as np

from agent_voice.audio.recorder import EnergyCommandRecorder


class EnergyCommandRecorderTest(unittest.TestCase):
    def test_stops_after_min_duration_and_end_silence(self):
        recorder = EnergyCommandRecorder(
            sample_rate=1000,
            frame_ms=100,
            min_duration_ms=200,
            max_duration_ms=1000,
            end_silence_ms=200,
            energy_threshold=0.01,
        )
        frames = [
            np.ones(100, dtype=np.float32) * 0.1,
            np.ones(100, dtype=np.float32) * 0.1,
            np.zeros(100, dtype=np.float32),
            np.zeros(100, dtype=np.float32),
        ]

        recorded = recorder.collect_from_reader(lambda: frames.pop(0))

        self.assertEqual(len(recorded), 400)

    def test_forces_stop_at_max_duration(self):
        recorder = EnergyCommandRecorder(
            sample_rate=1000,
            frame_ms=100,
            min_duration_ms=200,
            max_duration_ms=300,
            end_silence_ms=900,
            energy_threshold=0.01,
        )
        frames = [np.ones(100, dtype=np.float32) * 0.1 for _ in range(10)]

        recorded = recorder.collect_from_reader(lambda: frames.pop(0))

        self.assertEqual(len(recorded), 300)


if __name__ == "__main__":
    unittest.main()
