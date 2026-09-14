from __future__ import annotations
from typing import Any
import requests
from urllib.parse import urljoin
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

from src.clients.api_response import ApiResponse


class BaseClient:
    """
    Enterprise Base HTTP Client for API Test Automation.

    Key Production Features:
    1. Reusable requests.Session for TCP Connection Pooling (Keep-Alive).
    2. Precision Timeouts: (connect_timeout, read_timeout) tuple to eliminate test suite hangs.
    3. Resilient Retries: Configured with urllib3.util.Retry for transient 502/503/504 errors.
       (Note: Retries only safe/idempotent methods to prevent duplicate mutations).
    4. Robust URL Normalization: Eliminates double-slash or missing slash bugs.
    5. Returns ApiResponse wrapper for expressive, fluent test assertions.
    """

    def __init__(
        self,
        base_url: str,
        timeout: tuple[float, float] = (3.05, 10.0),
        max_retries: int = 3,
        default_headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout

        # 1. Initialize persistent session
        self.session = requests.Session()

        # 2. Configure default headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Atlassian-SDET-Framework/1.0",
        }
        if default_headers:
            headers.update(default_headers)
        self.session.headers.update(headers)

        # 3. Mount Retry Strategy onto connection pool
        if max_retries > 0:
            retry_strategy = Retry(
                total=max_retries,
                backoff_factor=0.5,  # 0.5s, 1.0s, 2.0s exponential backoff
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS"],  # Idempotent only!
                raise_on_status=False,  # Let ApiResponse handle status verification
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def _build_url(self, endpoint: str) -> str:
        """Safely join base_url and endpoint without duplicate slashes."""
        return urljoin(self.base_url, endpoint.lstrip("/"))

    def _send_request(self, method: str, endpoint: str, **kwargs) -> ApiResponse:
        """Internal dispatcher that injects trace IDs, applies timeouts, and wraps response."""
        import uuid

        url = self._build_url(endpoint)
        
        # Apply default timeout if caller didn't supply one
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        # Dynamic correlation ID per request for observability
        request_headers = kwargs.get("headers", {})
        if "X-Request-ID" not in request_headers:
            request_headers["X-Request-ID"] = str(uuid.uuid4())
        kwargs["headers"] = request_headers

        raw_response = self.session.request(method=method, url=url, **kwargs)
        return ApiResponse(raw_response)

    def get(self, endpoint: str, params: dict[str, Any] | None = None, **kwargs) -> ApiResponse:
        return self._send_request("GET", endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Any | None = None, **kwargs) -> ApiResponse:
        return self._send_request("POST", endpoint, json=json, **kwargs)

    def put(self, endpoint: str, json: Any | None = None, **kwargs) -> ApiResponse:
        return self._send_request("PUT", endpoint, json=json, **kwargs)

    def patch(self, endpoint: str, json: Any | None = None, **kwargs) -> ApiResponse:
        return self._send_request("PATCH", endpoint, json=json, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> ApiResponse:
        return self._send_request("DELETE", endpoint, **kwargs)

    def close(self):
        """Close the underlying session and free socket connections."""
        self.session.close()
