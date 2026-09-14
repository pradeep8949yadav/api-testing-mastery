# Atlassian SDET & API Test Automation Mastery

Production-grade API Test Automation curriculum, frameworks, and engineering notes targeting Senior SDET / API Automation Architect standards (Atlassian track).

---

## 🎯 Progress Tracker

| Module | Title | Status |
| :--- | :--- | :--- |
| **01** | The Request Journey, Layer Failures & SDET Mental Model | 🟢 Complete |
| **02** | Terminal-First API Debugging with cURL & Wire Inspection | 🟢 Complete |
| **03** | Resilient Python HTTP Engine (`Session`, Timeouts, Retries) | 🟢 Complete |
| **04** | Test Data Modeling (`dataclass` vs `Pydantic` vs `dict`) | 🟢 Complete |
| **05** | Pytest Deep Dive (Fixtures, Scopes, Isolation, Parametrization) | 🟢 Complete |
| **06** | Enterprise Framework Client Architecture (`BaseClient` & Domains) | 🟢 Complete |
| **07** | CRUD API Testing & Test Isolation Patterns | 🟢 Complete |
| **08** | Contract & JSON Schema Validation | 🟡 In Progress |
| **09** | Authentication Engines (JWT, OAuth 2.0, Refresh Tokens) | ⚪ Planned |
| **10** | API Security & OWASP Top 10 (Focus: BOLA / IDOR) | ⚪ Planned |
| **11** | Database Assertions with SQL & PostgreSQL | ⚪ Planned |
| **12** | Mocking & Service Virtualization | ⚪ Planned |
| **13** | Asynchronous APIs, Polling & Webhooks | ⚪ Planned |
| **14** | Advanced Query Testing (Pagination, Filtering, Sorting) | ⚪ Planned |
| **15** | Concurrency, Race Conditions & Lost Updates | ⚪ Planned |
| **16** | Performance & Load Testing with Locust (RPS, Latency p95/p99) | ⚪ Planned |
| **17** | Test Flakiness, Determinism & Smart Retries | ⚪ Planned |
| **18** | Docker & Containerized Test Environments | ⚪ Planned |
| **19** | CI/CD Automation Pipeline (GitHub Actions) | ⚪ Planned |
| **20** | Atlassian-Style Capstone Project & Mock SDET Interview | ⚪ Capstone |

---

## 📂 Repository Structure

```text
api-testing-mastery/
├── README.md               # Curriculum roadmap and live tracking
├── docs/                   # Architectural notes, mental models, interview deep dives
│   ├── 01_REQUEST_JOURNEY_AND_SDET_MINDSET.md
│   ├── 02_TERMINAL_CURL_DEBUGGING.md
│   └── 03_HTTP_CLIENT_ENGINE_ARCHITECTURE.md
├── src/                    # Production test client and utilities
│   ├── clients/
│   ├── models/
│   └── utils/
└── tests/                  # Pytest test suites (functional, contract, security)
```
