# Module 10: API Security & OWASP Top 10 (Focus: BOLA / IDOR)

## 1. What is BOLA / IDOR?
**BOLA (Broken Object Level Authorization)**, historically known as **IDOR (Insecure Direct Object Reference)**, is the #1 vulnerability on the **OWASP API Security Top 10**.

* **Vertical Privilege Escalation (RBAC / Module 09):** A low-privilege user accesses high-privilege functionality (e.g. `Viewer` deleting a project).
* **Horizontal Privilege Escalation (BOLA / Module 10):** A user accesses resources belonging to another user with the same privilege level (e.g. User A accessing User B's private project).

---

## 2. The Architectural Defect
Standard API gateways and auth middleware only verify **Authentication (AuthN)**:
```text
Client Request ──► Gateway: "Is token valid?" ──► YES ──► Controller: db.findById(req.id) ──► DATA LEAKED!
```
The framework does not know **who owns the data**. Ownership verification MUST happen at the data access layer:
$$\text{SELECT} * \text{FROM projects WHERE id} = :project\_id \;\mathbf{AND}\; tenant\_id = :authenticated\_tenant$$

---

## 3. Defense Trade-off: 403 Forbidden vs 404 Not Found

| Scenario | Return Code | Security Impact |
| :--- | :--- | :--- |
| **Public Multi-Tenant SaaS (Cross-Org)** | **`404 Not Found`** | **Zero Metadata Leakage:** Attackers cannot enumerate IDs to discover whether a resource exists. (The GitHub/AWS S3 standard). |
| **Intra-Organization / Same Team** | **`403 Forbidden`** | **Explicit Access Control:** User knows the resource exists but requires elevated team permissions. |

---

## 4. The 5 Core Security Test Scenarios

1. **Cross-Tenant Read Attack (GET):** Authenticated User B attempts to read User A's private resource $\rightarrow$ `404 Not Found`.
2. **Cross-Tenant Mutation Attack (PATCH/PUT):** User B attempts to modify User A's project metadata $\rightarrow$ `404 Not Found`.
3. **Cross-Tenant Destruction Attack (DELETE):** User B attempts to delete User A's project $\rightarrow$ `404 Not Found`.
4. **Tenant Parameter Spoofing:** User B passes `?tenant_id=org_alice` or `{"tenant_id": "org_alice"}` in request to trick the server $\rightarrow$ Server ignores body/query params and relies strictly on cryptographically verified JWT claims.
5. **Legitimate Owner Lifecycle (Happy Path):** User A can perform full CRUD on their own resources without interference $\rightarrow$ `200/204`.
