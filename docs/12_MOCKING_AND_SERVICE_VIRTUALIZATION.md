# Module 12: Mocking & Service Virtualization

## 1. Unit Mocking vs. Service Virtualization

| Dimension | Unit Mocking (`unittest.mock`) | Service Virtualization (`responses`, `WireMock`) |
| :--- | :--- | :--- |
| **Layer** | In-process Python function / method level | Network / HTTP wire transport level |
| **What Runs?** | Mock replaces the class entirely; no HTTP serialization or networking code executes | Real HTTP client, connection pooling, serialization, headers, retries, and timeouts all execute |
| **Primary Goal** | Test isolated internal class logic | Test integration, resilience, and error handling against external dependencies |
| **Production Risk** | High false confidence (serialization bugs or header mistakes pass silently) | High fidelity (wire contract is strictly verified) |

---

## 2. Why Virtualize 3rd-Party Dependencies?

In enterprise architectures (Atlassian Jira, Stripe, Twilio, AWS), automated tests cannot depend on live external APIs:
1. **Cost & Rate Limits:** 1,000 CI builds executing 100 payment calls each would cost thousands of dollars and trigger rate limits (`429 Too Many Requests`).
2. **Determinism & Flakiness:** External network hiccups (e.g. transient `502 Bad Gateway`) cause tests to fail randomly.
3. **Chaos & Failure Injection:** It is impossible to force a live external service to return `504 Gateway Timeout` or simulate network partitions on demand.

---

## 3. The 4 Critical Failure Scenarios to Virtualize

1. **Transient 5xx Outage & Retry Recovery:**
   * Virtualize service returning `503 Service Unavailable` on attempts 1 and 2, followed by `200 OK` on attempt 3.
   * Verifies that the client's exponential backoff and retry budget successfully self-heal.
2. **Gateway Timeout Injection:**
   * Virtualize an unresponsive upstream server triggering `requests.exceptions.Timeout`.
   * Verifies that the client honors its strict timeout SLA rather than hanging indefinitely.
3. **Idempotency Key & Wire Inspection:**
   * Inspect the virtualized wire to verify that `Idempotency-Key` and `X-Request-ID` headers are transmitted accurately.
4. **Catastrophic Outage (Retry Exhaustion):**
   * Virtualize persistent 500/503 errors.
   * Verifies that the client exhausts its retry limit and returns a clean failure without leaking unhandled exceptions.
