from __future__ import annotations
import time
from typing import Literal
import jwt

JWT_SECRET_KEY = "atlassian-sdet-super-secret-key-production"
JWT_ALGORITHM = "HS256"


def create_token(
    user_id: str,
    role: Literal["Admin", "Developer", "Viewer"] = "Developer",
    expires_in_seconds: int = 900,
    secret_key: str = JWT_SECRET_KEY,
) -> str:
    """Generate a standard cryptographically signed JWT token."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def create_expired_token(user_id: str, role: Literal["Admin", "Developer", "Viewer"] = "Viewer") -> str:
    """Generate a token that expired 1 hour in the past."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now - 7200,
        "exp": now - 3600,  # Expired 1 hour ago
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_tampered_token(user_id: str, role: Literal["Admin", "Developer", "Viewer"] = "Admin") -> str:
    """Generate a token signed with an invalid/rogue secret key to simulate tampering."""
    return create_token(user_id=user_id, role=role, secret_key="untrusted-attacker-secret-key")
