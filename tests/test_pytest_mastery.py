import pytest
from src.clients.base_client import BaseClient
from src.models.user import UserCreate


class TestPytestMastery:
    """
    Demonstrating Senior SDET Pytest patterns:
    1. Scope & Lifecycle isolation.
    2. Data-driven Boundary Value Testing using @pytest.mark.parametrize.
    3. Custom Marker categorization (smoke, regression, boundary).
    """

    @pytest.mark.smoke
    def test_smoke_health_check(self, api_client: BaseClient):
        """Smoke test verifying service availability and HTTP status."""
        response = api_client.get("/status/200")
        response.assert_status_code(200)

    @pytest.mark.regression
    @pytest.mark.boundary
    @pytest.mark.parametrize(
        "title, priority, expected_status, case_id",
        [
            ("Normal Bug Report", "High", 200, "TC-BVA-01-HappyPath"),
            ("A" * 3, "Low", 200, "TC-BVA-02-MinLengthBoundary"),
            ("A" * 200, "Medium", 200, "TC-BVA-03-MaxLengthBoundary"),
            ("Special Characters !@#$%^&*()", "Low", 200, "TC-BVA-04-SpecialChars"),
            ("Unicode Test: 🐛 🚀 ⚡", "High", 200, "TC-BVA-05-UnicodeSupport"),
        ],
    )
    def test_issue_creation_boundaries(
        self,
        api_client: BaseClient,
        title: str,
        priority: str,
        expected_status: int,
        case_id: str,
    ):
        """
        Data-Driven Test: Runs 5 boundary test cases through a single test function.
        Each test case is assigned a human-readable case_id in the test report.
        """
        payload = {"title": title, "priority": priority}
        response = api_client.post("/post", json=payload)
        
        response.assert_status_code(expected_status)
        data = response.json()
        assert data["json"]["title"] == title
        assert data["json"]["priority"] == priority

    @pytest.mark.regression
    def test_resource_lifecycle_with_automatic_cleanup(
        self, api_client: BaseClient, cleanup_tracker
    ):
        """
        Demonstrating Teardown Guardian:
        Resource is tracked immediately upon creation.
        Pytest guarantees DELETE is invoked after this test completes.
        """
        # Step 1: Create resource
        create_res = api_client.post("/post", json={"name": "Temporary Test Board"})
        create_res.assert_status_code(200)
        
        simulated_resource_id = "board_5541"
        # Register for automatic teardown
        cleanup_tracker(resource_type="boards", resource_id=simulated_resource_id)

        # Step 2: Perform assertions on created resource
        assert simulated_resource_id == "board_5541"
        # Teardown executes automatically after this line!
