import unittest

from agent_voice.pipeline import CommandOutcome, CommandPipeline
from agent_voice.transport.http_client import BusinessResponse


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response or BusinessResponse(accepted=True, code="OK", message="accepted", feedback="已处理")
        self.error = error
        self.payloads = []

    def send_command(self, payload):
        self.payloads.append(payload)
        if self.error:
            raise self.error
        return self.response


class CommandPipelineTest(unittest.TestCase):
    def test_process_text_sends_matched_command(self):
        client = FakeClient()
        pipeline = CommandPipeline(device_id="device-1", app_version="0.1.0", client=client)

        outcome = pipeline.process_text("调取患者 123456", asr_confidence=0.91)

        self.assertEqual(outcome.status, "sent")
        self.assertEqual(outcome.intent, "fetch_patient")
        self.assertEqual(outcome.feedback, "已处理")
        self.assertEqual(len(client.payloads), 1)
        self.assertEqual(client.payloads[0]["params"], {"patient_id": "123456"})

    def test_process_text_does_not_send_unknown_command(self):
        client = FakeClient()
        pipeline = CommandPipeline(device_id="device-1", app_version="0.1.0", client=client)

        outcome = pipeline.process_text("随便说一句", asr_confidence=0.91)

        self.assertEqual(outcome.status, "no_match")
        self.assertIn("未匹配指令", outcome.message)
        self.assertIn("调取患者123456", outcome.message)
        self.assertNotIn("no_rule_matched", outcome.message)
        self.assertEqual(client.payloads, [])

    def test_process_text_surfaces_send_error(self):
        client = FakeClient(error=TimeoutError("timeout"))
        pipeline = CommandPipeline(device_id="device-1", app_version="0.1.0", client=client)

        outcome = pipeline.process_text("调取患者 123456", asr_confidence=0.91)

        self.assertEqual(outcome.status, "error")
        self.assertIn("timeout", outcome.message)
        self.assertEqual(len(client.payloads), 1)


if __name__ == "__main__":
    unittest.main()
