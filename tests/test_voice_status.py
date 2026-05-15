import json
import tempfile
import unittest
from pathlib import Path

from agent_voice.voice_status import DEFAULT_STATUS_PATH, read_voice_status, write_voice_status


class VoiceStatusTest(unittest.TestCase):
    def test_writes_and_reads_latest_voice_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "last_voice_event.json"

            write_voice_status(path, event="command_result", asr_text="调取患者123456", outcome_status="sent")
            status = read_voice_status(path)

            self.assertEqual(status["event"], "command_result")
            self.assertEqual(status["asr_text"], "调取患者123456")
            self.assertEqual(status["outcome_status"], "sent")
            self.assertIn("updated_at", status)
            json.dumps(status, ensure_ascii=False)

    def test_missing_status_returns_empty_dict(self):
        self.assertEqual(read_voice_status(Path("missing.json")), {})

    def test_default_status_path_is_writable_user_location(self):
        self.assertTrue(DEFAULT_STATUS_PATH.is_absolute())
        self.assertNotIn("release/AgentVoice-macos", DEFAULT_STATUS_PATH.as_posix())


if __name__ == "__main__":
    unittest.main()
