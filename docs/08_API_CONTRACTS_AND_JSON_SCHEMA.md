# Module 08: API Contracts & JSON Schema Validation

## 1. Why Contract Testing is Mission-Critical
In distributed architectures, API backends serve multiple independent consumers:
* Web Single-Page Applications (SPAs)
* iOS and Android Native Mobile Apps (which users do not upgrade simultaneously)
* Third-party developers, integrations, and plugins (e.g. Jira Ecosystem)

If an API response structure breaks, un-updated mobile apps crash on launch and third-party consumers experience runtime failures.

---

## 2. Breaking vs Non-Breaking Changes

| Change Type | Examples | Backward-Compatible? |
| :--- | :--- | :--- |
| **Non-Breaking** | Adding a new response field, adding an optional query param, relaxing constraints | ✅ **Safe** |
| **Breaking** | Renaming a field, deleting a field, changing field data type (string $\rightarrow$ int), making an optional request field mandatory | 💥 **Dangerous** |

---

## 3. Safe Migration Strategies

1. **URL-Based API Versioning:**
   * Introduce `/api/v2/...` while maintaining `/api/v1/...` concurrently.
   * Provide a formal deprecation schedule (e.g. 6–12 months) before decommissioning v1.
2. **The "Expand and Contract" Pattern (Parallel Evolution):**
   * **Phase 1 (Expand):** Backend returns *both* old and new fields (`lead_email` and `owner_email`).
   * **Phase 2 (Migrate):** Clients are systematically migrated to consume `owner_email`.
   * **Phase 3 (Contract):** Once telemetry confirms zero traffic on `lead_email`, the field is deprecated and removed.

---

## 4. Implementation: JSON Schema Draft-07
Using Python's `jsonschema` library:
```python
from src.utils.schema_validator import validate_contract

# Validates data types, regex patterns, required keys, and disallows unexpected fields
validate_contract(response.json(), "project_schema.json")
```
Contract violation tests guarantee that missing required keys, type mutations, and schema drift are caught in the CI/CD pipeline before release.
