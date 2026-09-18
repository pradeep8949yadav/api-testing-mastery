# Module 11: Database Assertions & Direct SQL Verification

## 1. The White-Box SDET Mindset
In black-box API testing, a `201 Created` or `204 No Content` response only confirms that the HTTP layer succeeded. It does not guarantee:
1. **Schema Integrity:** Were all columns mapped correctly or silently dropped by the ORM?
2. **Audit Invariants:** Did `created_at`, `updated_at`, and `version` populate as expected?
3. **Ghost Writes:** Did a failed request (e.g. `409 Conflict` or `422 Unprocessable`) dirty the database before throwing an error?
4. **Soft Deletion:** Did a `DELETE` request hard-delete the record, or preserve the audit trail with `deleted_at` set and `is_active = 0`?

---

## 2. Dual-Channel Verification Pattern

```text
[API Request] ──► [HTTP Endpoint] ──► [Database]
                                          ▲
[Pytest Assertion] ◄── Direct SQL Query ──┘
```

1. **Dual Assertions on Mutation:**
   * Assert HTTP response: `status_code == 201`, JSON schema matches.
   * Assert DB row: `SELECT * FROM table WHERE id = :id` matches exact payload + default audit values (`version = 1`, `is_active = 1`).
2. **Negative Invariant Assertion (Zero Ghost Writes):**
   * Trigger validation failure (`422`) or key collision (`409`).
   * Assert DB row count: `SELECT COUNT(*) FROM table WHERE key = :key` MUST BE `0`.
3. **Soft Delete Contract Assertion:**
   * Execute `DELETE /resource/{id}` $\rightarrow$ returns `204 No Content`.
   * Public API `GET /resource/{id}` $\rightarrow$ returns `404 Not Found`.
   * Direct SQL `SELECT is_active, deleted_at FROM table WHERE id = :id` $\rightarrow$ row exists, `is_active = 0`, `deleted_at IS NOT NULL`.
