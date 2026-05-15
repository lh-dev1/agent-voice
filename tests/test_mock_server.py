import json
import unittest
from urllib.request import Request, urlopen

from agent_voice.mock_server import BusinessMockServer


class BusinessMockServerTest(unittest.TestCase):
    def test_accepts_command_payload(self):
        server = BusinessMockServer(host="127.0.0.1", port=0)
        server.start()
        try:
            body = json.dumps({"request_id": "rid-1", "intent": "fetch_patient"}).encode("utf-8")
            request = Request(
                f"{server.base_url}/api/voice/commands",
                data=body,
                headers={"Content-Type": "application/json", "X-Request-Id": "rid-1"},
                method="POST",
            )

            with urlopen(request, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(response.status, 200)
            self.assertTrue(payload["accepted"])
            self.assertEqual(server.received[0]["request_id"], "rid-1")
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
