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
