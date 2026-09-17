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

