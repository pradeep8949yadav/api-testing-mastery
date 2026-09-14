# Module 05: Pytest Mastery for API Test Engineers

## 1. Centralized Fixtures & Root `conftest.py`

In professional test architectures, fixtures are never imported manually via `from x import y`. 
Pytest automatically discovers fixtures in root or directory-level `conftest.py` files:

```python
# conftest.py
@pytest.fixture(scope="session")
def api_client():
    client = BaseClient(...)
    yield client
    client.close()  # Clean teardown
```

---

## 2. The 5 Fixture Scopes & Test Isolation

| Scope | Execution Frequency | Risk if Mutated | Correct Use Case |
| :--- | :--- | :--- | :--- |
| **`session`** | Once per entire test suite run | Catastrophic (test order dependencies) | Read-only connection pools, global configs, auth tokens |
| **`package`** | Once per package directory | High | Sub-system level setup |
| **`module`** | Once per `.py` file | Medium | Starting a local mock server or reading static dataset |
| **`class`** | Once per test class | Medium | Shared read-only class setup |
| **`function`** | Before/after **every single test** | **Zero (100% Isolated)** | Entity creation (users, projects, issues) with automatic cleanup |

---

## 3. The Teardown Guardian (`yield`)

Never leave test data hanging in backend databases. Pytest fixtures use `yield` to guarantee cleanup even if test assertions fail:

```python
@pytest.fixture(scope="function")
def cleanup_tracker(api_client):
    created_resources = []
    
    def _track(resource_type: str, resource_id: str):
        created_resources.append((resource_type, resource_id))
        return resource_id
        
    yield _track
    
    # Teardown executes in reverse order of creation
    for res_type, res_id in reversed(created_resources):
        api_client.delete(f"/{res_type}/{res_id}")
```

---

## 4. Data-Driven Testing with `@pytest.mark.parametrize`

Instead of writing 10 separate test functions to test boundary conditions, use parametrization:
* **Equivalence Partitioning (EP)**: Valid partition vs Invalid partition.
* **Boundary Value Analysis (BVA)**: Min boundary ($3$), Max boundary ($200$), Empty ($0$), Exceeds ($201$).
* **Security & Injections**: Special characters, Unicode emojis, SQL/XSS strings.

---

## 5. Custom Test Markers & Execution Subsets
Configured via `pytest.ini`:
```bash
# Run only critical smoke tests (e.g. before merging a pull request)
pytest -m smoke

# Run full boundary regression
pytest -m boundary
```
