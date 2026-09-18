from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status, Response, Query
from pydantic import BaseModel, Field
import threading

app = FastAPI(title="Atlassian Mock API Service", version="1.0.0")

# In-Memory Thread-Safe Data Store
_lock = threading.Lock()
_projects_db: Dict[str, Dict[str, Any]] = {}
_id_counter = 100


class ProjectCreateModel(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    key: str = Field(..., min_length=2, max_length=10)
    lead_email: str
    description: Optional[str] = None


class ProjectUpdateModel(BaseModel):
    name: str
    key: str
    lead_email: str
    description: Optional[str] = None


class ProjectPatchModel(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    lead_email: Optional[str] = None
    description: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "healthy", "service": "atlassian-mock-api"}


@app.post("/api/v1/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateModel):
    global _id_counter
    with _lock:
        key_upper = payload.key.upper()
        # Enforce unique key constraint (returns 409 Conflict)
        for proj in _projects_db.values():
            if proj["key"] == key_upper:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Project key '{key_upper}' already exists in organization.",
                )

        # Enforce strict email format check (must have characters before and after @)
        parts = payload.lead_email.strip().split("@")
        if len(parts) != 2 or not parts[0] or "." not in parts[1] or not parts[1].split(".")[0]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid lead email format: '{payload.lead_email}'.",
            )

        _id_counter += 1
        project_id = f"PROJ-{_id_counter}"
        record = {
            "id": project_id,
            "name": payload.name,
            "key": key_upper,
            "lead_email": payload.lead_email,
            "description": payload.description,
        }
        _projects_db[project_id] = record
        return record


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str):
    with _lock:
        if project_id not in _projects_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        return _projects_db[project_id]


@app.put("/api/v1/projects/{project_id}")
def replace_project(project_id: str, payload: ProjectUpdateModel):
    """PUT: Full resource replacement."""
    with _lock:
        if project_id not in _projects_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        record = {
            "id": project_id,
            "name": payload.name,
            "key": payload.key.upper(),
            "lead_email": payload.lead_email,
            "description": payload.description,
        }
        _projects_db[project_id] = record
        return record


@app.patch("/api/v1/projects/{project_id}")
def update_project_fields(project_id: str, payload: ProjectPatchModel):
    """PATCH: Partial resource modification."""
    with _lock:
        if project_id not in _projects_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        record = _projects_db[project_id]
        updates = payload.model_dump(exclude_unset=True)
        if "key" in updates and updates["key"]:
            updates["key"] = updates["key"].upper()
        record.update(updates)
        _projects_db[project_id] = record
        return record


@app.delete("/api/v1/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str):
    with _lock:
        if project_id not in _projects_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        del _projects_db[project_id]
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/v1/projects")
def list_projects(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
):
    with _lock:
        all_items = list(_projects_db.values())
        start = (page - 1) * limit
        end = start + limit
        return {
            "page": page,
            "limit": limit,
            "total": len(all_items),
            "items": all_items[start:end],
        }


@app.delete("/api/v1/internal/reset", status_code=status.HTTP_200_OK)
def reset_db():
    with _lock:
        _projects_db.clear()
        return {"status": "reset complete"}


# ─── AUTHENTICATION & AUTHORIZATION ENGINE ───

from fastapi import Header
import jwt

JWT_SECRET_KEY = "atlassian-sdet-super-secret-key-production"
JWT_ALGORITHM = "HS256"


class LoginModel(BaseModel):
    username: str
    password: str
    role: Optional[str] = "Developer"


class RefreshTokenModel(BaseModel):
    refresh_token: str


@app.post("/api/v1/auth/login", status_code=status.HTTP_200_OK)
def login(payload: LoginModel):
    """Simulate OAuth/JWT token issuance with short-lived access and long-lived refresh tokens."""
    import time
    if payload.password == "wrong_password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )
    
    now = int(time.time())
    access_payload = {
        "sub": payload.username,
        "role": payload.role,
        "type": "access",
        "iat": now,
        "exp": now + 900,  # 15 minutes
    }
    refresh_payload = {
        "sub": payload.username,
        "role": payload.role,
        "type": "refresh",
        "iat": now,
        "exp": now + 604800,  # 7 days
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "role": payload.role,
    }


@app.post("/api/v1/auth/refresh", status_code=status.HTTP_200_OK)
def refresh_token(payload: RefreshTokenModel):
    """Validate refresh token and issue a fresh access token."""
    import time
    try:
        claims = jwt.decode(payload.refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please re-authenticate.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token signature.",
        )

    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Only refresh tokens are permitted on this endpoint.",
        )

    now = int(time.time())
    new_access_payload = {
        "sub": claims.get("sub"),
        "role": claims.get("role"),
        "type": "access",
        "iat": now,
        "exp": now + 900,
    }
    new_access_token = jwt.encode(new_access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return {
        "access_token": new_access_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "role": claims.get("role"),
    }



def _verify_auth_token(authorization: Optional[str]) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
        )
    token = authorization.split("Bearer ")[1].strip()
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except (jwt.InvalidTokenError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature.",
        )


@app.delete("/api/v1/secure/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def secure_delete_project(project_id: str, authorization: Optional[str] = Header(default=None)):
    """
    Role-Based Access Control (RBAC) Protected Endpoint:
    - Requires valid JWT in Authorization header.
    - Requires role == 'Admin'. Viewers receive 403 Forbidden.
    """
    user_claims = _verify_auth_token(authorization)
    if user_claims.get("role") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{user_claims.get('role')}' does not have Admin permission to delete projects.",
        )

    with _lock:
        if project_id not in _projects_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        del _projects_db[project_id]
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── OBJECT-LEVEL AUTHORIZATION (BOLA / IDOR PROTECTED) ───

class TenantProjectCreateModel(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    key: str = Field(..., min_length=2, max_length=10)
    lead_email: str
    description: Optional[str] = None


@app.post("/api/v1/tenant/projects", status_code=status.HTTP_201_CREATED)
def create_tenant_project(payload: TenantProjectCreateModel, authorization: Optional[str] = Header(default=None)):
    """Create a project strictly bound to the authenticated tenant's identity."""
    user_claims = _verify_auth_token(authorization)
    tenant_id = user_claims.get("tenant_id", user_claims.get("sub"))
    owner = user_claims.get("sub")

    global _id_counter
    with _lock:
        key_upper = payload.key.upper()
        _id_counter += 1
        project_id = f"PROJ-{_id_counter}"
        record = {
            "id": project_id,
            "name": payload.name,
            "key": key_upper,
            "lead_email": payload.lead_email,
            "description": payload.description,
            "tenant_id": tenant_id,
            "owner": owner,
        }
        _projects_db[project_id] = record
        return record


@app.get("/api/v1/tenant/projects/{project_id}")
def get_tenant_project(project_id: str, authorization: Optional[str] = Header(default=None)):
    """
    BOLA/IDOR Protected Read:
    Returns 404 if project does not exist OR belongs to another tenant (Zero Metadata Leakage).
    """
    user_claims = _verify_auth_token(authorization)
    caller_tenant = user_claims.get("tenant_id", user_claims.get("sub"))

    with _lock:
        project = _projects_db.get(project_id)
        if not project or project.get("tenant_id") != caller_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        return project


@app.patch("/api/v1/tenant/projects/{project_id}")
def update_tenant_project(
    project_id: str,
    payload: ProjectPatchModel,
    authorization: Optional[str] = Header(default=None),
):
    """
    BOLA/IDOR Protected Mutation:
    Only the resource owner/tenant can modify it. Discards any injected tenant_id.
    """
    user_claims = _verify_auth_token(authorization)
    caller_tenant = user_claims.get("tenant_id", user_claims.get("sub"))

    with _lock:
        project = _projects_db.get(project_id)
        if not project or project.get("tenant_id") != caller_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        
        updates = payload.model_dump(exclude_unset=True)
        # Prevent tenant parameter injection
        updates.pop("tenant_id", None)
        updates.pop("owner", None)
        if "key" in updates and updates["key"]:
            updates["key"] = updates["key"].upper()

        project.update(updates)
        _projects_db[project_id] = project
        return project


@app.delete("/api/v1/tenant/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant_project(project_id: str, authorization: Optional[str] = Header(default=None)):
    """
    BOLA/IDOR Protected Destruction:
    Prevents cross-tenant project deletion.
    """
    user_claims = _verify_auth_token(authorization)
    caller_tenant = user_claims.get("tenant_id", user_claims.get("sub"))

    with _lock:
        project = _projects_db.get(project_id)
        if not project or project.get("tenant_id") != caller_tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        del _projects_db[project_id]
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── SQL PERSISTENCE ENDPOINTS (MODULE 11 DATABASE INVARIANTS) ───

import sqlite3
from src.utils.db_client import DB_FILE_PATH


def _get_sql_connection():
    conn = sqlite3.connect(DB_FILE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.post("/api/v1/sql/projects", status_code=status.HTTP_201_CREATED)
def create_sql_project(payload: ProjectCreateModel, tenant_id: str = Query(default="org_default")):
    key_upper = payload.key.upper()
    # Validate email
    parts = payload.lead_email.strip().split("@")
    if len(parts) != 2 or not parts[0] or "." not in parts[1] or not parts[1].split(".")[0]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid lead email format: '{payload.lead_email}'.",
        )

    with _get_sql_connection() as conn:
        # Check uniqueness
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sql_projects WHERE key = ?", (key_upper,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project key '{key_upper}' already exists.",
            )

        import uuid
        project_id = f"PROJ-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
            INSERT INTO sql_projects (id, key, name, lead_email, description, tenant_id, version, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1)
        """, (project_id, key_upper, payload.name, payload.lead_email, payload.description, tenant_id))
        conn.commit()

        cursor.execute("SELECT * FROM sql_projects WHERE id = ?", (project_id,))
        return dict(cursor.fetchone())


@app.get("/api/v1/sql/projects/{project_id}")
def get_sql_project(project_id: str):
    with _get_sql_connection() as conn:
        cursor = conn.cursor()
        # Soft-delete filter: only active, non-deleted rows
        cursor.execute("SELECT * FROM sql_projects WHERE id = ? AND is_active = 1 AND deleted_at IS NULL", (project_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
        return dict(row)


@app.patch("/api/v1/sql/projects/{project_id}")
def patch_sql_project(project_id: str, payload: ProjectPatchModel):
    with _get_sql_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sql_projects WHERE id = ? AND is_active = 1", (project_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

        updates = payload.model_dump(exclude_unset=True)
        new_name = updates.get("name", existing["name"])
        new_desc = updates.get("description", existing["description"])
        new_lead = updates.get("lead_email", existing["lead_email"])
        new_key = updates.get("key", existing["key"]).upper()

        cursor.execute("""
            UPDATE sql_projects 
            SET name = ?, description = ?, lead_email = ?, key = ?, 
                version = version + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_name, new_desc, new_lead, new_key, project_id))
        conn.commit()

        cursor.execute("SELECT * FROM sql_projects WHERE id = ?", (project_id,))
        return dict(cursor.fetchone())


@app.delete("/api/v1/sql/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sql_project(project_id: str):
    """Soft delete endpoint: Sets is_active = 0 and sets deleted_at timestamp."""
    with _get_sql_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sql_projects WHERE id = ? AND is_active = 1", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

        cursor.execute("""
            UPDATE sql_projects 
            SET is_active = 0, deleted_at = CURRENT_TIMESTAMP, version = version + 1
            WHERE id = ?
        """, (project_id,))
        conn.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── ASYNCHRONOUS JOBS & WEBHOOKS (MODULE 13) ───

import hmac
import hashlib
from fastapi import Request

from fastapi.responses import JSONResponse

_async_jobs: dict[str, dict[str, Any]] = {}
WEBHOOK_SHARED_SECRET = "atlassian-sdet-webhook-secret-production-key"


class ExportJobRequest(BaseModel):
    job_type: str = "issues_csv"
    fail_intentionally: bool = False
    never_finish: bool = False


@app.post("/api/v1/jobs/export", status_code=status.HTTP_202_ACCEPTED)
def start_export_job(payload: ExportJobRequest):
    """
    HTTP 202 Accepted Pattern:
    Accepts job, assigns job_id, sets Location and Retry-After headers, and returns 202.
    """
    import uuid
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    with _lock:
        _async_jobs[job_id] = {
            "job_id": job_id,
            "status": "QUEUED",
            "progress_pct": 0,
            "fail": payload.fail_intentionally,
            "hang": payload.never_finish,
            "polls": 0,
        }

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        headers={
            "Location": f"/api/v1/jobs/export/{job_id}",
            "Retry-After": "0",
        },
        content={
            "job_id": job_id,
            "status": "QUEUED",
            "message": "Export job accepted and scheduled for asynchronous background execution.",
        },
    )


@app.get("/api/v1/jobs/export/{job_id}")
def get_export_job_status(job_id: str):
    """Poll endpoint that simulates asynchronous background execution."""
    with _lock:
        if job_id not in _async_jobs:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")
        
        job = _async_jobs[job_id]
        job["polls"] += 1

        if job["hang"]:
            job["status"] = "PROCESSING"
            job["progress_pct"] = 15
            return JSONResponse(content=job, headers={"Retry-After": "0"})

        if job["fail"] and job["polls"] >= 2:
            job["status"] = "FAILED"
            job["error"] = "Worker process terminated unexpectedly during CSV serialization."
            return JSONResponse(content=job)

        if job["polls"] == 1:
            job["status"] = "PROCESSING"
            job["progress_pct"] = 50
            return JSONResponse(content=job, headers={"Retry-After": "0"})
        else:
            job["status"] = "COMPLETED"
            job["progress_pct"] = 100
            job["download_url"] = f"https://storage.atlassian.net/exports/{job_id}.csv"
            return JSONResponse(content=job)



@app.post("/api/v1/webhooks/listener", status_code=status.HTTP_200_OK)
async def receive_webhook(request: Request):
    """
    Webhook Receiver with HMAC-SHA256 Signature Verification:
    Validates X-Hub-Signature-256 header against the raw body using constant-time comparison.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")

    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed X-Hub-Signature-256 header.",
        )

    provided_signature = signature_header.split("sha256=")[1].strip()
    expected_signature = hmac.new(
        WEBHOOK_SHARED_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cryptographic HMAC signature verification failed. Untrusted webhook source.",
        )

    return {"status": "event_acknowledged", "payload_bytes": len(raw_body)}




