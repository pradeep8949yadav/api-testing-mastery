from __future__ import annotations
from typing import Any
from src.clients.base_client import BaseClient
from src.clients.api_response import ApiResponse


class IssuesClient(BaseClient):
    """
    Domain-specific client for Atlassian Jira Issues API.
    Encapsulates issue lifecycle: creation, transitions (Workflow), and deletion.
    """

    def create_issue(
        self,
        project_key: str,
        title: str,
        priority: str = "Medium",
        description: str | None = None,
        **kwargs
    ) -> ApiResponse:
        payload: dict[str, Any] = {
            "project_key": project_key.upper(),
            "title": title,
            "priority": priority,
            "status": "Backlog",
        }
        if description:
            payload["description"] = description
        return self.post("/post", json=payload, **kwargs)

    def get_issue(self, issue_id: str | int, **kwargs) -> ApiResponse:
        return self.get("/get", params={"issue_id": issue_id}, **kwargs)

    def transition_status(self, issue_id: str | int, target_status: str, **kwargs) -> ApiResponse:
        """Move issue through Jira workflow (e.g. Backlog -> In Progress -> Done)."""
        return self.patch(
            "/patch",
            json={"issue_id": issue_id, "target_status": target_status},
            **kwargs
        )

    def delete_issue(self, issue_id: str | int, **kwargs) -> ApiResponse:
        return self.delete("/delete", params={"issue_id": issue_id}, **kwargs)
