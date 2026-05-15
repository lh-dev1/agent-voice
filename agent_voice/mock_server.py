"""Local mock business endpoint for end-to-end desktop testing."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class BusinessMockServer:
    """Small HTTP server accepting Agent Voice command payloads."""

    def __init__(self, host: str = "127.0.0.1", port: int = 18080) -> None:
        """Create a mock server bound to host and port."""

        self.host = host
        self.port = port
        self.received: list[dict[str, Any]] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        """Return the base URL for the running mock server."""

        if self._server is None:
            return f"http://{self.host}:{self.port}"
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        """Start the mock server in a background thread."""

        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                if self.path != "/api/voice/commands":
                    self.send_error(404, "Not found")
                    return
                length = int(self.headers.get("Content-Length") or "0")
                body = self.rfile.read(length)
                try:
                    payload = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON")
                    return
                owner.received.append(payload)
                response = {
                    "accepted": True,
                    "code": "OK",
                    "message": "accepted",
                    "feedback": f"已接收 {payload.get('intent', 'command')}",
                }
                data = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, name="agent-voice-mock-server", daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        """Run the mock server in the foreground until interrupted."""

        self._server = ThreadingHTTPServer((self.host, self.port), self._foreground_handler())
        try:
            self._server.serve_forever()
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the mock server and release the socket."""

        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _foreground_handler(self) -> type[BaseHTTPRequestHandler]:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                if self.path != "/api/voice/commands":
                    self.send_error(404, "Not found")
                    return
                length = int(self.headers.get("Content-Length") or "0")
                body = self.rfile.read(length)
                try:
                    payload = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON")
                    return
                owner.received.append(payload)
                print(json.dumps(payload, ensure_ascii=False), flush=True)
                response = {
                    "accepted": True,
                    "code": "OK",
                    "message": "accepted",
                    "feedback": f"已接收 {payload.get('intent', 'command')}",
                }
                data = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, format: str, *args: Any) -> None:
                return

        return Handler
