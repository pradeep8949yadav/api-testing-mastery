# Module 01: The Request Journey & SDET Mental Model

## 1. Complete Journey of `GET /users/123`

```
[Test Suite]
     │
     ▼ (1. DNS Resolution)
[DNS Server] ──► Returns IP: 203.0.113.10
     │
     ▼ (2. TCP 3-Way Handshake + TLS 1.3 Handshake)
[Load Balancer / Reverse Proxy (e.g. NGINX / Envoy)]
     │
     ▼ (3. TLS Termination & Rate Limiting)
[API Gateway (Kong / Cloudflare / Custom)]
     │
     ▼ (4. Routing & Auth Verification)
[App Server (FastAPI / Django / Spring)]
     │
     ├──► (5. Cache Lookup) ──► [Redis Cache]
     │
     └──► (6. Database Query) ──► [PostgreSQL / Aurora]
```

---

## 2. Where API Tests Fail & How They Manifest

| Layer | Failure Mode | Manifestation in Python Automation |
| :--- | :--- | :--- |
| **DNS** | Unresolvable hostname / DNS timeout | `requests.exceptions.ConnectionError: [Errno -2] Name or service not known` |
| **TLS/SSL** | Expired cert, handshake mismatch | `SSLError: CERTIFICATE_VERIFY_FAILED` |
| **TCP / Socket** | Firewall dropped packet, socket pool exhausted | `TimeoutError` or `ConnectionResetError` |
| **Load Balancer** | Upstream nodes down, body size limit | `502 Bad Gateway` or `413 Payload Too Large` |
| **API Gateway** | Expired token, rate limit exceeded | `401 Unauthorized`, `429 Too Many Requests` |
| **App Logic** | Unhandled exception, null pointer | `500 Internal Server Error` |
| **Cache** | Cache invalidation failure (stale data) | Update succeeded, but immediate GET returns stale value |
| **Database** | Constraint violation, deadlocks | `409 Conflict` (good) or `500 Internal Server Error` (unhandled) |

---

## 3. AuthN vs AuthZ (401 vs 403)

* **401 Unauthorized (AuthN - Authentication)**:
  * "Who are you?"
  * The identity is missing, malformed, or invalid (e.g., missing `Authorization` header, expired JWT).
* **403 Forbidden (AuthZ - Authorization)**:
  * "I know who you are, but you do not have permission to do this."
  * The user is validly logged in, but their role/permissions do not grant access to the resource (e.g., Viewer attempting to delete an Organization).

---

## 4. Idempotency & Safe Methods

* **Safe Methods**: Read-only, no server state change (`GET`, `HEAD`, `OPTIONS`).
* **Idempotent Methods**: $f(f(x)) = f(x)$. Executing $N$ times leaves the server in the exact same state as executing once.
  * `GET`: Idempotent & Safe.
  * `PUT`: Idempotent (full resource replacement).
  * `DELETE`: Idempotent (subsequent calls return `404`, but resource remains deleted).
  * `POST`: **Non-Idempotent** by default (subsequent calls create duplicate records).

### Handling Non-Idempotent Retries in Production: `Idempotency-Key`
Clients generate a unique UUID per transaction:
```http
POST /api/v1/payments/checkout
Idempotency-Key: 7b9a5c89-2e6b-4e1b-b49b-733f7c191a62
```
The server stores the result against the key in Redis/DB; subsequent retries with the same key replay the previous response without charging the card again.
