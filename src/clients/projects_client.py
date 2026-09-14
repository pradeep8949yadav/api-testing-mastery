from __future__ import annotations
from typing import Any
from src.clients.base_client import BaseClient
from src.clients.api_response import ApiResponse


class ProjectsClient(BaseClient):
    """
    Domain-specific client for Atlassian Project Management APIs.
    
    Why Domain Clients over raw API calls?
    1. Single Source of Truth for Route Endpoints (/api/v1/projects).
    2. Readability: tests say `projects_client.create_project(...)` instead of raw HTTP dictionaries.
    3. Resilient Refactoring: If Jira API changes v1 to v2, you update only this class!
    """

    PROJECTS_ENDPOINT = "/post"  # Using reflection endpoint for simulation

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
            "key": key.upper(),
            "lead_email": lead_email,
        }
        if description:
            payload["description"] = description
        return self.post(self.PROJECTS_ENDPOINT, json=payload, **kwargs)

    def get_project(self, project_id: str | int, **kwargs) -> ApiResponse:
        return self.get(f"/get", params={"project_id": project_id}, **kwargs)

    def update_project(self, project_id: str | int, updates: dict[str, Any], **kwargs) -> ApiResponse:
        return self.put(f"/put", json={"project_id": project_id, **updates}, **kwargs)

    def delete_project(self, project_id: str | int, **kwargs) -> ApiResponse:
        return self.delete(f"/delete", params={"project_id": project_id}, **kwargs)

    def list_projects(self, page: int = 1, limit: int = 50, **kwargs) -> ApiResponse:
        return self.get(f"/get", params={"page": page, "limit": limit}, **kwargs)
