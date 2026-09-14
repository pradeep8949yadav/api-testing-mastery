from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class IssueCreate(BaseModel):
    """
    Request model for creating an issue in a Jira-like system.
    
    Why Pydantic over a plain Python dict?
    1. Validation: Automatically catches missing required fields or type errors before calling the API.
    2. Serialization: Convert cleanly to dict/json with .model_dump() or .model_dump_json().
    3. Autocomplete: Full IDE type safety, no risk of typos like payload['prioirty'].
    """
    title: str = Field(..., min_length=3, max_length=200, description="Summary/title of the issue")
    priority: str = Field(default="Medium", description="Priority level: Low, Medium, High, Blocker")
    description: Optional[str] = Field(default=None, description="Detailed problem description")


class IssueResponse(BaseModel):
    """
    Response model for validating that the backend returned a contract-compliant issue.
    """
    id: str | int
    title: str
    priority: str
    status: str = "Open"
