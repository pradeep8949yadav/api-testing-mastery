# Module 09: Authentication & Authorization Engines (JWT, RBAC)

## 1. AuthN vs AuthZ on the Wire

| Dimension | Authentication (AuthN) | Authorization (AuthZ / RBAC) |
| :--- | :--- | :--- |
| **Core Question** | "Who are you?" | "Are you permitted to perform this action?" |
| **Status Code** | **`401 Unauthorized`** | **`403 Forbidden`** |
| **Typical Failures** | Missing header, expired token (`exp`), malformed token, tampered cryptographic signature | Valid user identity, but insufficient role (e.g. `Viewer` attempting `DELETE` or administrative settings) |

---

## 2. JWT Anatomy (`Header.Payload.Signature`)
* **Header:** Algorithm declaration (`HS256`, `RS256`).
* **Payload (Claims):**
  * `sub`: Subject / User Identifier.
  * `role`: User privileges (`Admin`, `Developer`, `Viewer`).
  * `exp`: Unix timestamp when token becomes invalid.
  * `iat`: Unix timestamp when token was issued.
* **Signature:** HMACSHA256 signature generated with the server's private secret. If an attacker modifies the payload (e.g. changes `role` from `Viewer` to `Admin`), the signature fails validation.

---

## 3. The 5 Core Security Test Scenarios

1. **Happy Path:** Valid `Admin` token executes protected operation $\rightarrow$ `204 No Content`.
2. **Missing Token:** Request without `Authorization` header $\rightarrow$ `401 Unauthorized`.
3. **Expired Token:** Request with `exp` in the past $\rightarrow$ `401 Unauthorized`.
4. **Tampered Signature:** Token signed with attacker/rogue secret key $\rightarrow$ `401 Unauthorized`.
5. **RBAC Privilege Escalation (Vertical Authorization):** Authenticated `Viewer` token attempting `DELETE` $\rightarrow$ `403 Forbidden`.
