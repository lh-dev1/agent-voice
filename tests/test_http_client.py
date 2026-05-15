import json
import unittest
from urllib.error import HTTPError

from agent_voice.mock_server import BusinessMockServer
from agent_voice.transport.http_client import BusinessClient, BusinessResponse


class FakeHttpResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class BusinessClientTest(unittest.TestCase):
    def test_sends_payload_with_request_id_and_agent_version(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return FakeHttpResponse(200, {"accepted": True, "code": "OK", "message": "accepted"})

        client = BusinessClient(
            base_url="http://127.0.0.1:18080",
            command_path="/api/voice/commands",
            timeout_ms=3000,
            retry=1,
            app_version="0.1.0",
            opener=opener,
        )
        response = client.send_command({"request_id": "rid-1", "intent": "fetch_patient"})

        self.assertEqual(response, BusinessResponse(accepted=True, code="OK", message="accepted", feedback=None))
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:18080/api/voice/commands")
        self.assertEqual(timeout, 3.0)
        self.assertEqual(request.headers["X-request-id"], "rid-1")
        self.assertEqual(request.headers["X-agent-voice-version"], "0.1.0")

    def test_retries_5xx_once_with_same_request_id(self):
        request_ids = []

        def opener(request, timeout):
            request_ids.append(request.headers["X-request-id"])
            if len(request_ids) == 1:
                raise HTTPError(request.full_url, 500, "server error", hdrs=None, fp=None)
            return FakeHttpResponse(200, {"accepted": True, "code": "OK", "message": "accepted"})

        client = BusinessClient(
            base_url="http://127.0.0.1:18080",
            command_path="/api/voice/commands",
            timeout_ms=3000,
            retry=1,
            app_version="0.1.0",
            opener=opener,
        )
        response = client.send_command({"request_id": "rid-2", "intent": "fetch_patient"})

        self.assertTrue(response.accepted)
        self.assertEqual(request_ids, ["rid-2", "rid-2"])

    def test_does_not_retry_4xx(self):
        calls = 0

        def opener(request, timeout):
            nonlocal calls
            calls += 1
            raise HTTPError(request.full_url, 400, "bad request", hdrs=None, fp=None)

        client = BusinessClient(
            base_url="http://127.0.0.1:18080",
            command_path="/api/voice/commands",
            timeout_ms=3000,
            retry=1,
            app_version="0.1.0",
            opener=opener,
        )

        with self.assertRaises(HTTPError):
            client.send_command({"request_id": "rid-3", "intent": "fetch_patient"})
        self.assertEqual(calls, 1)

    def test_default_opener_posts_to_real_http_endpoint(self):
        server = BusinessMockServer(host="127.0.0.1", port=0)
        server.start()
        try:
            client = BusinessClient(
                base_url=server.base_url,
                command_path="/api/voice/commands",
                timeout_ms=3000,
                retry=0,
                app_version="0.1.0",
            )

            response = client.send_command({"request_id": "rid-4", "intent": "fetch_patient"})

            self.assertTrue(response.accepted)
            self.assertEqual(server.received[0]["request_id"], "rid-4")
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
