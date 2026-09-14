import pytest
from src.clients.projects_client import ProjectsClient


class TestCrudLifecycleAndEdgeCases:
    """
    Production CRUD test suite for Atlassian Project Management REST API.
    Covers state transitions, 409 conflicts, 404 ghost checks, 204 no-content,
    and PUT vs PATCH semantic differences.
    """

    def test_complete_crud_lifecycle(self, projects_client: ProjectsClient):
        """
        Verify the full end-to-end lifecycle of a resource:
        Create (201) -> Read (200) -> Delta Update (200) -> Delete (204) -> Ghost Check (404).
        """
        # 1. CREATE: POST /api/v1/projects -> 201 Created
        create_res = projects_client.create_project(
            name="Jira Core Engine",
            key="CORE",
            lead_email="lead@atlassian.com",
            description="Core issue processing pipeline"
        )
        create_res.assert_status_code(201)
        project_data = create_res.json()
        project_id = project_data["id"]
        assert project_data["key"] == "CORE"

        # 2. READ: GET /api/v1/projects/{id} -> 200 OK
        get_res = projects_client.get_project(project_id)
        get_res.assert_status_code(200)
        assert get_res.json()["name"] == "Jira Core Engine"

        # 3. UPDATE: PATCH /api/v1/projects/{id} -> 200 OK
        patch_res = projects_client.patch_project(
            project_id,
            updates={"name": "Jira Core Engine v2"}
        )
        patch_res.assert_status_code(200)
        # Ensure name updated while other fields remained intact
        assert patch_res.json()["name"] == "Jira Core Engine v2"
        assert patch_res.json()["key"] == "CORE"

        # 4. DELETE: DELETE /api/v1/projects/{id} -> 204 No Content
        del_res = projects_client.delete_project(project_id)
        del_res.assert_status_code(204)
        # Wire reality check: 204 body MUST be empty!
        assert del_res.text == ""

        # 5. GHOST CHECK: GET /api/v1/projects/{id} -> 404 Not Found
        ghost_res = projects_client.get_project(project_id)
        ghost_res.assert_status_code(404)

    def test_duplicate_key_conflict_returns_409(self, projects_client: ProjectsClient):
        """
        Business Rule: Project key must be unique across the organization.
        Creating a duplicate key must return 409 Conflict (not 400 or 500).
        """
        # Step 1: Create initial project with key "PAY"
        first = projects_client.create_project(
            name="Payments v1",
            key="PAY",
            lead_email="pay@atlassian.com"
        )
        first.assert_status_code(201)

        # Step 2: Attempt to create another project with same key "PAY"
        duplicate = projects_client.create_project(
            name="Payments v2",
            key="PAY",
            lead_email="billing@atlassian.com"
        )
        duplicate.assert_status_code(409)
        assert "already exists" in duplicate.json()["detail"]

    def test_delete_nonexistent_resource_returns_404(self, projects_client: ProjectsClient):
        """Verify attempting to delete an unknown ID returns 404 cleanly without crashing server."""
        res = projects_client.delete_project("PROJ-NON-EXISTENT-999")
        res.assert_status_code(404)

    def test_put_vs_patch_semantics(self, projects_client: ProjectsClient):
        """
        Verify architectural distinction between PUT (full replace) and PATCH (delta modification).
        """
        # Create base project with description
        init_res = projects_client.create_project(
            name="Audit Log Service",
            key="AUDIT",
            lead_email="sec@atlassian.com",
            description="Compliance logging"
        )
        init_res.assert_status_code(201)
        proj_id = init_res.json()["id"]

        # PUT: Replaces resource. Notice description is omitted/None
        put_res = projects_client.replace_project(
            proj_id,
            payload={
                "name": "Audit Service Replaced",
                "key": "AUDIT",
                "lead_email": "sec-team@atlassian.com",
                "description": None  # Explicitly cleared in full replacement
            }
        )
        put_res.assert_status_code(200)
        assert put_res.json()["description"] is None

        # PATCH: Modifies only specified fields; others remain untouched
        patch_res = projects_client.patch_project(
            proj_id,
            updates={"lead_email": "new-lead@atlassian.com"}
        )
        patch_res.assert_status_code(200)
        assert patch_res.json()["lead_email"] == "new-lead@atlassian.com"
        assert patch_res.json()["name"] == "Audit Service Replaced"  # Preserved!

    @pytest.mark.parametrize("invalid_email", [
        "not-an-email",
        "missing-at.com",
        "@missing-user.com",
    ])
    def test_malformed_email_validation_failure(
        self, projects_client: ProjectsClient, invalid_email: str
    ):
        """Verify input validation rejects malformed email with 422 Unprocessable Entity."""
        res = projects_client.create_project(
            name="Invalid Project",
            key="INV",
            lead_email=invalid_email
        )
        res.assert_status_code(422)
