from __future__ import annotations
import json
from typing import Any
import requests


class ApiResponse:
    """
    Production-grade HTTP Response wrapper for test automation.
    
    Why wrap requests.Response?
    1. Clean test assertions: response.assert_status_code(200) gives crystal-clear failure messages.
    2. Safe JSON decoding: Doesn't crash with JSONDecodeError if server returns 500 HTML.
    3. Latency tracking: Easily assert performance SLA (e.g. response.assert_latency_below(500)).
    4. Access to raw underlying response whenever needed.
    """

    def __init__(self, response: requests.Response):
        self._response = response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._response.headers)

    @property
    def elapsed_ms(self) -> float:
        """Returns request round-trip latency in milliseconds."""
        return self._response.elapsed.total_seconds() * 1000

    @property
    def text(self) -> str:
        return self._response.text

    def json(self) -> Any:
        """Safely parse JSON or return None if body is not valid JSON."""
        try:
            return self._response.json()
        except (ValueError, json.JSONDecodeError):
            return None

    def assert_status_code(self, expected_status: int | list[int]) -> ApiResponse:
        """
        Fluent assertion for HTTP status code.
        Example:
            response.assert_status_code(201)
            response.assert_status_code([200, 204])
        """
        allowed = [expected_status] if isinstance(expected_status, int) else expected_status
        if self.status_code not in allowed:
            raise AssertionError(
                f"Status Code Mismatch!\n"
                f"  Expected : {allowed}\n"
                f"  Actual   : {self.status_code}\n"
                f"  URL      : {self._response.request.method} {self._response.url}\n"
                f"  Body     : {self.text[:500]}"
            )
        return self

    def assert_latency_below(self, max_ms: float) -> ApiResponse:
        """Assert that the API response latency meets SLA limits."""
        if self.elapsed_ms > max_ms:
            raise AssertionError(
                f"Latency SLA Violated!\n"
                f"  Max Allowed : {max_ms} ms\n"
                f"  Actual      : {self.elapsed_ms:.2f} ms\n"
                f"  Endpoint    : {self._response.request.method} {self._response.url}"
            )
        return self

    def __repr__(self) -> str:
        return f"<ApiResponse [{self.status_code}] ({self.elapsed_ms:.1f}ms)>"
