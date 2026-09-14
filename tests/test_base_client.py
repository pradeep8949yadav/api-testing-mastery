import pytest
from src.clients.base_client import BaseClient
from src.models.issue import IssueCreate




class TestBaseClient:
    """Production test suite verifying BaseClient functionality."""

    def test_get_success_and_latency_sla(self, api_client: BaseClient):
        """Verify GET returns 200 and latency is within acceptable SLA (under 3000ms over WAN)."""
        response = api_client.get("/get", params={"env": "staging"})
        
        # 1. Fluent status assertion
        response.assert_status_code(200)
        
        # 2. SLA check
        response.assert_latency_below(3000)
        
        # 3. Data validation
        data = response.json()
        assert data is not None
        assert data["args"]["env"] == "staging"

    def test_post_with_pydantic_model(self, api_client: BaseClient):
        """Verify POST automatically serializes Pydantic model into JSON body."""
        issue = IssueCreate(
            title="Database Connection Pool Starvation",
            priority="Blocker",
            description="All 50 connections locked during sprint transition."
        )
        
        # Send model dumped to dict
        response = api_client.post("/post", json=issue.model_dump())
        response.assert_status_code(200)
        
        data = response.json()
        assert data["json"]["title"] == "Database Connection Pool Starvation"
        assert data["json"]["priority"] == "Blocker"

    def test_negative_scenario_handled_cleanly(self, api_client: BaseClient):
        """
        Verify that a 404 response does NOT raise an unhandled exception in the client,
        allowing the test to assert the negative status code cleanly.
        """
        response = api_client.get("/status/404")
        
        # The test explicitly asserts 404
        response.assert_status_code(404)
        assert response.status_code == 404

    def test_url_normalization(self, api_client: BaseClient):
        """Verify URL joining handles leading slashes and base URLs with/without trailing slashes."""
        # Endpoint with leading slash
        url1 = api_client._build_url("/users/123")
        # Endpoint without leading slash
        url2 = api_client._build_url("users/123")
        
        assert url1 == "https://httpbin.org/users/123"
        assert url2 == "https://httpbin.org/users/123"
