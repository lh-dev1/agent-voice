import json
import tempfile
import unittest
from pathlib import Path

from agent_voice.config_writer import update_config


class ConfigWriterTest(unittest.TestCase):
    def test_updates_nested_config_values_without_dropping_other_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "app": {"device_id": "device-1"},
                        "audio": {"device_index": None, "sample_rate": 16000},
                        "transport": {"base_url": "http://old", "retry": 1},
                        "recorder": {"energy_threshold": 0.008},
                    }
                ),
                encoding="utf-8",
            )

            update_config(
                path,
                {
                    "audio.device_index": 3,
                    "transport.base_url": "http://127.0.0.1:18080",
                    "recorder.energy_threshold": 0.012,
                },
            )

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["app"]["device_id"], "device-1")
            self.assertEqual(saved["audio"]["sample_rate"], 16000)
            self.assertEqual(saved["audio"]["device_index"], 3)
            self.assertEqual(saved["transport"]["base_url"], "http://127.0.0.1:18080")
            self.assertEqual(saved["transport"]["retry"], 1)
            self.assertEqual(saved["recorder"]["energy_threshold"], 0.012)


if __name__ == "__main__":
    unittest.main()
