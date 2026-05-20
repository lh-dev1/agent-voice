import unittest
from datetime import datetime, timedelta, timezone

import numpy as np

from agent_voice.config import AppConfig
from agent_voice.ui.qt_widget import _format_voice_status
from agent_voice.voice_loop import (
    _microphone_status_payload,
    _should_write_mic_level,
    _wake_keywords_score,
    _wake_keywords_threshold,
)


class VoiceLoopStatusTest(unittest.TestCase):
    def test_builds_microphone_activity_payload_from_frame_level(self):
        frame = np.ones(160, dtype=np.float32) * 0.02

        payload = _microphone_status_payload(frame, threshold=0.008)

        self.assertEqual(payload["event"], "mic_level")
        self.assertTrue(payload["active"])
        self.assertEqual(payload["level"], 0.02)
        self.assertEqual(payload["level_percent"], 83)

    def test_builds_quiet_microphone_payload_below_threshold(self):
        frame = np.ones(160, dtype=np.float32) * 0.001

        payload = _microphone_status_payload(frame, threshold=0.008)

        self.assertEqual(payload["event"], "mic_level")
        self.assertFalse(payload["active"])
        self.assertEqual(payload["level_percent"], 4)

    def test_formats_microphone_level_for_widget(self):
        text = _format_voice_status({"event": "mic_level", "active": True, "level_percent": 23})

        self.assertEqual(text, "麦克风：有声音，音量 23%\n最近识别：等待唤醒词")

    def test_does_not_overwrite_recent_microphone_asr_result_with_level(self):
        now = datetime(2026, 5, 12, 4, 20, 0, tzinfo=timezone.utc)
        status = {"event": "mic_asr_result", "updated_at": (now - timedelta(seconds=2)).isoformat()}

        self.assertFalse(_should_write_mic_level(status, now=now, hold_seconds=6))

    def test_writes_microphone_level_after_result_hold_expires(self):
        now = datetime(2026, 5, 12, 4, 20, 0, tzinfo=timezone.utc)
        status = {"event": "mic_asr_result", "updated_at": (now - timedelta(seconds=7)).isoformat()}

        self.assertTrue(_should_write_mic_level(status, now=now, hold_seconds=6))

    def test_missing_wake_sensitivity_defaults_to_high_hit_rate_setting(self):
        config = AppConfig.from_dict(
            {
                "app": {"device_id": "clinic-room-01-pc-03"},
                "transport": {"base_url": "http://127.0.0.1:18080"},
            }
        )

        self.assertEqual(config.wake.sensitivity, 0.9)

    def test_high_sensitivity_lowers_threshold_and_boosts_keyword_score(self):
        self.assertEqual(_wake_keywords_threshold(0.9), 0.1)
        self.assertEqual(_wake_keywords_score(0.9), 2.0)

    def test_wake_tuning_clamps_extreme_sensitivity_values(self):
        self.assertEqual(_wake_keywords_threshold(1.2), 0.05)
        self.assertEqual(_wake_keywords_score(1.2), 2.125)
        self.assertEqual(_wake_keywords_threshold(-1.0), 0.9)
        self.assertEqual(_wake_keywords_score(-1.0), 1.0)


if __name__ == "__main__":
    unittest.main()
