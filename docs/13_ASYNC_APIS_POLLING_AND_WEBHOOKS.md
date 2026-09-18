# Module 13: Asynchronous APIs, Polling & Webhooks

## 1. Why Asynchronous HTTP?
Operations exceeding typical gateway timeouts (e.g. 5–30 seconds) cannot be executed synchronously:
* Large bulk exports (CSV/PDF reports).
* Heavy background computations & AI inference.
* External bank payment settlements.

Holding HTTP connections open causes:
1. Thread starvation on backend web servers.
2. Load balancer connection timeouts (`504 Gateway Timeout`).
3. Network connection drops on mobile/unstable clients.

---

## 2. Pattern A: HTTP 202 Accepted + Smart Polling

```text
Client                                             Server
  │                                                  │
  ├─── POST /api/v1/jobs/export ────────────────────►│
  │◄── 202 Accepted ─────────────────────────────────┤
  │    Headers: Location: /jobs/123                  │
  │             Retry-After: 1                       │
  │    Body: {"job_id": "123", "status": "QUEUED"}   │
  │                                                  │
  │  [Poll Loop with Backoff & Deadline]            │
  ├─── GET /jobs/123 ───────────────────────────────►│
  │◄── 200 OK {"status": "PROCESSING", "pct": 50} ───┤
  │                                                  │
  ├─── GET /jobs/123 ───────────────────────────────►│
  │◄── 200 OK {"status": "COMPLETED", "url": "..."} ─┤
```

### The 4 Mandatory Safety Rules for Polling in Test Suites:
1. **Hard Deadline (Timeout):** Never run `while True: sleep(1)`. Enforce an absolute wall-clock timeout (e.g. 10s) to prevent hanging CI pipelines.
2. **Maximum Attempt Cap:** Limit the total number of poll requests (e.g. max 15 requests).
3. **Fail-Fast Terminal States:** Do not wait for timeout if the job fails! If status is `FAILED` or `CANCELLED`, raise an immediate assertion error with error logs.
4. **Dynamic Backoff (`Retry-After`):** Respect server-provided `Retry-After` headers and apply exponential backoff to avoid DDoS-ing test servers.

---

## 3. Pattern B: Webhooks & HMAC Cryptographic Signatures

Instead of client polling, the server initiates an asynchronous HTTP `POST` to the client's registered webhook callback URL.

### Security: Payload Tampering & Spoofing Defense
To guarantee that the webhook actually originated from the genuine server (and not an attacker):
1. The server signs the raw body with a shared secret key using `HMAC-SHA256`:
   $$\text{Signature} = \text{HMAC-SHA256}(\text{Raw Body}, \;\text{WEBHOOK\_SECRET})$$
2. Server attaches the signature in the header:
   ```http
   X-Hub-Signature-256: sha256=a1b2c3d4e5f6...
   ```
3. The receiver recomputes the HMAC hash and compares it using constant-time comparison (`hmac.compare_digest`) to prevent timing attacks.
