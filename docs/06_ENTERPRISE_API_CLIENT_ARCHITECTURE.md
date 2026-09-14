# Module 06: Enterprise API Client Architecture & Domain Abstractions

## 1. The Anti-Pattern: Raw Endpoints in Test Files
If tests directly invoke:
```python
client.post("/api/v1/projects", json={"name": "Demo"})
```
Across 300 tests, endpoint URLs, query parameter formats, and payload structures are duplicated everywhere. If Atlassian changes `/api/v1/projects` to `/api/v2/workspaces/{id}/projects`, every test file breaks.

---

## 2. The Solution: Domain Client Pattern (API Page Object Model)
We separate **Transport** from **Business Domain**:

```
           ┌────────────────────────┐
           │       BaseClient       │ (Transport, Session Pooling,
           │                        │  Timeouts, Retries, Tracing)
           └───────────┬────────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
┌──────────────┐              ┌─────────────────┐
│ProjectsClient│              │  IssuesClient   │ (Domain Methods,
│              │              │                 │  Workflow Transitions)
└──────────────┘              └─────────────────┘
```

### Benefits:
1. **Single Source of Truth**: Route definitions exist in exactly one place.
2. **Readability**: Tests read like business requirements:
   ```python
   projects_client.create_project(name="Platform", key="PLT", lead="lead@atlassian.com")
   issues_client.transition_status(issue_id="PLT-101", target_status="In Progress")
   ```
3. **Workflow Encapsulation**: Domain clients handle entity transitions and state machines.

---

## 3. Observability & Correlation (`X-Request-ID`)
Every outgoing HTTP call automatically injects a unique UUID:
```http
X-Request-ID: 6a837798-c9c6-4d7e-8997-e1addfe38390
```
When a test fails in CI/CD, the SDET or developer copies the `X-Request-ID` from the test report and searches it in Datadog/Splunk/ELK to instantly find the exact backend logs, database queries, and stack traces.
