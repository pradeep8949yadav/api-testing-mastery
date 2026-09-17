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

---

## 4. The Dual-Token Lifecycle (Access + Refresh)

To balance strict security with a seamless user experience, production APIs utilize two tokens:

| Property | Access Token | Refresh Token |
| :--- | :--- | :--- |
| **Lifespan** | Short (e.g. 15 minutes) | Long (e.g. 7 to 30 days) |
| **Scope of Use** | Sent on every API request in `Authorization: Bearer` | Sent ONLY to `/api/v1/auth/refresh` |
| **Claim Type** | `"type": "access"` | `"type": "refresh"` |
| **Security Risk** | Leaked token expires quickly | Can be revoked server-side |

### Security Defense: Token Substitution Attack
An attacker might attempt to pass a short-lived Access Token to `/api/v1/auth/refresh` to reset their timer or confuse the service. 
The server must strictly assert `claims["type"] == "refresh"`; otherwise, return **`401 Unauthorized`**.

---

## 5. Enterprise Client Architecture: 401 Auto-Refresh Interceptor

In high-scale automated test suites (and real SDK clients), test cases should not manually handle 401s and token refresh logic.

The HTTP client engine implements an **Interceptor / Transparent Retry**:
1. Client sends request with current Access Token.
2. If server returns `401 Unauthorized` and a `refresh_token` is present:
   - Interceptor catches the `401`.
   - Interceptor calls `/api/v1/auth/refresh` to acquire a new Access Token.
   - Client updates its persistent session header (`Authorization: Bearer <new_token>`).
   - Interceptor retries the original request **exactly once** (`_is_retry=True`).
3. **Infinite Loop Protection:** If the refresh token is also expired/invalid, or the retry returns 401, the client halts further retries and bubbles up the response to the caller.

