# Module 03: Resilient HTTP Client Engine Architecture

## 1. Why Standalone `requests.get()` is an Anti-Pattern in Automation

* **No Connection Pooling**: Standalone calls tear down and recreate TCP/TLS connections on every request, adding hundreds of milliseconds of overhead per test.
* **No Default Timeout**: In Python `requests`, `timeout=None` by default. If a backend service deadlocks or firewall drops packets, the entire test suite hangs indefinitely.
* **Silent 4xx/5xx**: `requests` does not raise an exception on HTTP errors. Calling `.json()` on a 500 HTML response throws a confusing `JSONDecodeError`.
* **String Concatenation Bugs**: `base_url + "/issues/" + id` leads to bugs like `//issues` or missing slashes.

---

## 2. The Three Pillars of a Resilient Test Client

### Pillar 1: Connection Pooling via `requests.Session()`
Reuses existing TCP sockets for subsequent requests to the same host. Automatically persists shared headers (`Authorization`, `Accept`) and cookies.

### Pillar 2: Precision Timeouts `(connect, read)`
```python
timeout = (3.05, 27.0)
```
* **Connect timeout (3.05s)**: Time to complete the TCP handshake. Set slightly above 3.0s to allow for one TCP SYN retransmission cycle.
* **Read timeout (27.0s)**: Time allowed for backend database queries / business logic before returning data.

### Pillar 3: Resilient Retries via `HTTPAdapter`
```python
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

retry_strategy = Retry(
    total=3,
    backoff_factor=1,  # 1s, 2s, 4s backoff
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS"],  # Idempotent ONLY! No POST!
)
```

---

## 3. The `ApiResponse` Wrapper Pattern

Rather than returning a raw `dict` or calling `raise_for_status()` inside the client, we wrap the HTTP response:
* Exposes `status_code`, `json()`, `elapsed` (latency), `headers`.
* Allows negative test cases to cleanly assert expected 4xx codes without handling unexpected exceptions.
* Provides high-level assertion helpers: `response.assert_status(200)`.
