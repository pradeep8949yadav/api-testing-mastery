# Module 07: CRUD API Testing & State Isolation Patterns

## 1. The Core Operations & HTTP Status Semantics

| Verb | Endpoint | Success Code | Wire Invariant |
| :--- | :--- | :--- | :--- |
| **`POST`** | `/api/v1/projects` | `201 Created` | Returns newly generated `id` and created resource representation. |
| **`GET`** | `/api/v1/projects/{id}` | `200 OK` | Safe, read-only. Server state unchanged. |
| **`PUT`** | `/api/v1/projects/{id}` | `200 OK` | **Full Resource Replacement**. Omitted/unspecified fields reset to null/default. |
| **`PATCH`** | `/api/v1/projects/{id}` | `200 OK` | **Delta Modification**. Only targeted fields updated; all others preserved. |
| **`DELETE`**| `/api/v1/projects/{id}` | `204 No Content` | **Empty Body**. Attempting to parse JSON from 204 response will fail. |

---

## 2. Essential State Invariants (What an SDET Asserts)

1. **Post-Creation Persistence Check:**
   `POST` returns 201 $\rightarrow$ Follow-up `GET` verifies resource is actually in database.
2. **Post-Deletion Ghost Check:**
   `DELETE` returns 204 $\rightarrow$ Follow-up `GET` **must return 404 Not Found**.
3. **Duplicate Uniqueness Constraint:**
   Attempting to create duplicate unique keys (e.g. project key, email) must return **`409 Conflict`**, never 400 or 500.
4. **Idempotent Deletion Safety:**
   Deleting a non-existent or already deleted resource returns `404 Not Found` without crashing backend services.

---

## 3. Real Defect Logged (Case Study)
* **Bug Found via BVA:** The backend accepted `"@missing-user.com"` as a valid email because it only verified the presence of `@` and `.`.
* **Impact:** Corrupted user records with blank usernames in the database.
* **Fix Applied:** Enforced strict splitting and validation on both `parts[0]` (username) and `parts[1]` (domain).
