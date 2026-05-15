import json
import unittest
from datetime import datetime, timezone

from agent_voice.nlu.parser import ParseResult
from agent_voice.transport.schema import build_command_payload, generate_request_id


class SchemaTest(unittest.TestCase):
    def test_generates_request_id_with_timestamp_and_suffix(self):
        request_id = generate_request_id(now=datetime(2026, 5, 11, 6, 30, 12, tzinfo=timezone.utc), suffix="8f3a6c")

        self.assertEqual(request_id, "20260511-063012-8f3a6c")

    def test_builds_required_command_payload_fields(self):
        parse_result = ParseResult(
            matched=True,
            text="调取患者 123456",
            normalized_text="调取患者123456",
            intent="fetch_patient",
            params={"patient_id": "123456"},
            asr_confidence=0.86,
            parser_confidence=0.98,
        )

        payload = build_command_payload(
            parse_result=parse_result,
            device_id="clinic-room-01-pc-03",
            app_version="0.1.0",
            request_id="20260511-143012-8f3a6c",
            now=datetime(2026, 5, 11, 6, 30, 12, tzinfo=timezone.utc),
            duration_ms={"recording": 1820, "asr": 640, "parse": 2},
        )

        self.assertEqual(payload["version"], "1.0")
        self.assertEqual(payload["request_id"], "20260511-143012-8f3a6c")
        self.assertEqual(payload["device_id"], "clinic-room-01-pc-03")
        self.assertEqual(payload["source"], "desktop_voice_widget")
        self.assertEqual(payload["event_type"], "command")
        self.assertEqual(payload["intent"], "fetch_patient")
        self.assertEqual(payload["params"], {"patient_id": "123456"})
        self.assertEqual(payload["duration_ms"]["asr"], 640)
        json.dumps(payload)

    def test_rejects_unmatched_parse_result(self):
        parse_result = ParseResult(
            matched=False,
            text="未知",
            normalized_text="未知",
            intent=None,
            params={},
            asr_confidence=0.8,
            parser_confidence=0.0,
            reason="no_rule_matched",
        )

        with self.assertRaises(ValueError):
            build_command_payload(
                parse_result=parse_result,
                device_id="device",
                app_version="0.1.0",
                request_id="rid",
                now=datetime(2026, 5, 11, 6, 30, 12, tzinfo=timezone.utc),
                duration_ms={},
            )


if __name__ == "__main__":
    unittest.main()
