from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    """
    Contract model for creating a user.
    Enforces email format, strict roles, age boundaries, and default department.
    """
    email: str = Field(..., description="Corporate email address")
    role: Literal["Admin", "Developer", "Reporter"] = Field(
        ..., description="User role in Atlassian organization"
    )
    age: int = Field(..., ge=18, le=65, description="Age must be between 18 and 65")
    department: str = Field(default="Engineering", description="Assigned department")

    @field_validator("email")
    @classmethod
    def validate_corporate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError(f"Invalid email format: '{v}'")
        return v.lower().strip()


class UserResponse(BaseModel):
    """
    Contract model for validating API responses returned by the backend.
    """
    id: str | int
    email: str
    role: str
    is_active: bool = True
    department: str
