from __future__ import annotations
from typing import Any
from src.clients.base_client import BaseClient
from src.clients.api_response import ApiResponse


class ProjectsClient(BaseClient):
    """
    Domain-specific client for Atlassian Project Management REST APIs.
    Communicates with /api/v1/projects using proper REST semantics.
    """

    BASE_ENDPOINT = "/api/v1/projects"

    def create_project(
        self,
        name: str,
        key: str,
        lead_email: str,
        description: str | None = None,
        **kwargs
    ) -> ApiResponse:
        payload: dict[str, Any] = {
            "name": name,
            "key": key,
            "lead_email": lead_email,
        }
        if description is not None:
            payload["description"] = description
        return self.post(self.BASE_ENDPOINT, json=payload, **kwargs)

    def get_project(self, project_id: str | int, **kwargs) -> ApiResponse:
        return self.get(f"{self.BASE_ENDPOINT}/{project_id}", **kwargs)

    def replace_project(self, project_id: str | int, payload: dict[str, Any], **kwargs) -> ApiResponse:
        """PUT: Full replacement."""
        return self.put(f"{self.BASE_ENDPOINT}/{project_id}", json=payload, **kwargs)

    def patch_project(self, project_id: str | int, updates: dict[str, Any], **kwargs) -> ApiResponse:
        """PATCH: Partial modification."""
        return self.patch(f"{self.BASE_ENDPOINT}/{project_id}", json=updates, **kwargs)

    def delete_project(self, project_id: str | int, **kwargs) -> ApiResponse:
        """DELETE: Remove resource."""
        return self.delete(f"{self.BASE_ENDPOINT}/{project_id}", **kwargs)

    def list_projects(self, page: int = 1, limit: int = 10, **kwargs) -> ApiResponse:
        return self.get(self.BASE_ENDPOINT, params={"page": page, "limit": limit}, **kwargs)
