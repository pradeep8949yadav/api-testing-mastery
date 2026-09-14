import pytest
from src.clients.projects_client import ProjectsClient
from src.clients.issues_client import IssuesClient


class TestDomainClients:
    """Test suite verifying Domain Client abstraction layer and trace header injection."""

    def test_projects_client_create_and_trace_id(self, projects_client: ProjectsClient):
        """Verify project creation encapsulates payloads and injects X-Request-ID trace header."""
        response = projects_client.create_project(
            name="Atlassian Core Infrastructure",
            key="infra",
            lead_email="architect@atlassian.com",
            description="Mission-critical cloud platform"
        )
        response.assert_status_code(200)

        data = response.json()
        # Verify domain abstraction formatted payload
        assert data["json"]["name"] == "Atlassian Core Infrastructure"
        assert data["json"]["key"] == "INFRA"  # Normalized to uppercase
        assert data["json"]["lead_email"] == "architect@atlassian.com"

        # Verify automated correlation trace ID injection on the wire
        assert "X-Request-ID" in response.request_headers
        assert len(response.request_headers["X-Request-ID"]) > 10

    def test_issues_client_lifecycle_and_transitions(self, issues_client: IssuesClient):
        """Verify issue creation and Jira workflow state transitions."""
        # 1. Create Issue
        create_res = issues_client.create_issue(
            project_key="atlas",
            title="Fix Kafka consumer group rebalance lag",
            priority="High"
        )
        create_res.assert_status_code(200)
        assert create_res.json()["json"]["status"] == "Backlog"

        # 2. Transition Workflow Status (Backlog -> In Progress)
        transition_res = issues_client.transition_status(
            issue_id="ATLAS-409",
            target_status="In Progress"
        )
        transition_res.assert_status_code(200)
        assert transition_res.json()["json"]["target_status"] == "In Progress"
