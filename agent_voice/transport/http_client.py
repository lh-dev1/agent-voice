"""HTTP client for delivering parsed voice commands to the business system."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


Opener = Callable[[Request, float], Any]


@dataclass(frozen=True)
class BusinessResponse:
    """Normalized business endpoint response."""

    accepted: bool
    code: str
    message: str
    feedback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the response."""

        return {
            "accepted": self.accepted,
            "code": self.code,
            "message": self.message,
            "feedback": self.feedback,
        }


class BusinessClient:
    """Send command payloads with timeout, idempotency header, and bounded retry."""

    def __init__(
        self,
        base_url: str,
        command_path: str,
        timeout_ms: int,
        retry: int,
        app_version: str,
        opener: Opener | None = None,
        hmac_secret: str | None = None,
    ) -> None:
        """Create a business HTTP client."""

        if not base_url:
            raise ValueError("base_url is required")
        self.url = urljoin(base_url.rstrip("/") + "/", command_path.lstrip("/"))
        self.timeout_seconds = timeout_ms / 1000.0
        self.retry = max(0, int(retry))
        self.app_version = app_version
        self.opener = opener or _urlopen_with_timeout
        self.hmac_secret = hmac_secret

    def send_command(self, payload: dict[str, Any]) -> BusinessResponse:
        """POST one command payload, retrying timeout and 5xx failures only."""

        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            raise ValueError("payload.request_id is required")

        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        attempts = self.retry + 1
        for attempt in range(attempts):
            try:
                request = self._build_request(body=body, request_id=request_id)
                with self.opener(request, self.timeout_seconds) as response:
                    return self._parse_response(response)
            except HTTPError as exc:
                if 500 <= exc.code <= 599 and attempt + 1 < attempts:
                    continue
                raise
            except TimeoutError:
                if attempt + 1 < attempts:
                    continue
                raise
            except URLError:
                if attempt + 1 < attempts:
                    continue
                raise

        raise RuntimeError("unreachable transport retry state")

    def _build_request(self, body: bytes, request_id: str) -> Request:
        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": request_id,
            "X-Agent-Voice-Version": self.app_version,
        }
        if self.hmac_secret:
            signature = hmac.new(self.hmac_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            headers["X-Voice-Signature"] = signature
        return Request(self.url, data=body, headers=headers, method="POST")

    @staticmethod
    def _parse_response(response: Any) -> BusinessResponse:
        raw = response.read()
        data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        return BusinessResponse(
            accepted=bool(data.get("accepted")),
            code=str(data.get("code") or ""),
            message=str(data.get("message") or ""),
            feedback=data.get("feedback"),
        )


def _urlopen_with_timeout(request: Request, timeout: float) -> Any:
    return urlopen(request, timeout=timeout)
