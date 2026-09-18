import pytest
from src.clients.projects_client import ProjectsClient
from src.utils.db_client import db_client


class TestDatabaseAssertionsAndInvariants:
    """
    Module 11: Direct Database Assertions & Persistence Invariant Testing.
    
    Verifies:
    1. Schema & Audit Invariants: created_at, version=1, is_active=1 upon creation.
    2. Negative Persistence Invariant (Zero Ghost Writes): 409 Conflict leaves no uncommitted/orphaned rows.
    3. Mutation Invariants: PATCH increments optimistic version lock and updates audit timestamp.
    4. Soft-Delete Contract: DELETE hides resource from public API (404), but preserves DB row with deleted_at set.
    """

    @pytest.fixture(autouse=True)
    def clean_database(self):
        """Ensure test isolation by resetting database table before each test."""
        db_client.reset_database()
        yield
        db_client.reset_database()

    def test_dual_assertion_post_and_database_audit_fields(
        self, projects_client: ProjectsClient
    ):
        """
        Dual-Channel Verification:
        1. HTTP Assertion: API returns 201 Created and expected JSON response.
        2. Direct SQL Assertion: Database row exists with exact system audit fields (version=1, is_active=1, created_at).
        """
        payload = {
            "name": "Audit Tracked Project",
            "key": "AUDIT01",
            "lead_email": "lead@audit.org",
            "description": "Direct DB Assertion Verification",
        }
        res = projects_client.post("/api/v1/sql/projects", json=payload)
        res.assert_status_code(201)
        api_data = res.json()
        project_id = api_data["id"]

        # Direct SQL Assertion (Ground Truth)
        db_row = db_client.get_project_by_id(project_id)
        assert db_row is not None, f"Persistence Failure: Row for '{project_id}' was not found in SQLite table!"
        assert db_row["key"] == "AUDIT01"
        assert db_row["name"] == "Audit Tracked Project"
        assert db_row["version"] == 1, "Invariant Violation: Initial version must be 1"
        assert db_row["is_active"] == 1, "Invariant Violation: New project must be active"
        assert db_row["created_at"] is not None, "Invariant Violation: created_at must be populated by database"
        assert db_row["deleted_at"] is None, "Invariant Violation: deleted_at must be NULL on active record"

    def test_negative_persistence_invariant_no_ghost_writes_on_conflict(
        self, projects_client: ProjectsClient
    ):
        """
        Negative Invariant Verification:
        Attempting to create a duplicate project returns 409 Conflict.
        Direct SQL query confirms NO orphaned or partially written ghost row exists.
        """
        payload = {
            "name": "Original Key Project",
            "key": "UNIQUEKEY",
            "lead_email": "admin@atlassian.com",
        }
        # First valid create
        res1 = projects_client.post("/api/v1/sql/projects", json=payload)
        res1.assert_status_code(201)

        # Duplicate create attempt (must fail with 409)
        res2 = projects_client.post("/api/v1/sql/projects", json=payload)
        res2.assert_status_code(409)

        # Direct SQL negative assertion: Row count for 'UNIQUEKEY' must be exactly 1, not 2
        count = db_client.count_projects_by_key("UNIQUEKEY")
        assert count == 1, f"Ghost Write Detected! Expected 1 row in DB, but found {count}!"

    def test_mutation_database_invariant_version_bump_and_updated_at(
        self, projects_client: ProjectsClient
    ):
        """
        Mutation Invariant Verification:
        PATCH updates fields and causes the database engine to increment the version and updated_at.
        """
        # 1. Create project
        create_res = projects_client.post(
            "/api/v1/sql/projects",
            json={"name": "Initial Name", "key": "MUTATE01", "lead_email": "dev@test.org"},
        )
        create_res.assert_status_code(201)
        project_id = create_res.json()["id"]

        # 2. Patch project
        patch_res = projects_client.patch(
            f"/api/v1/sql/projects/{project_id}",
            json={"name": "Updated Name V2"},
        )
        patch_res.assert_status_code(200)

        # Direct SQL Assertion: version must be 2, name must be updated
        db_row = db_client.get_project_by_id(project_id)
        assert db_row is not None
        assert db_row["name"] == "Updated Name V2"
        assert db_row["version"] == 2, "Optimistic Lock Failure: version was not incremented to 2!"
        assert db_row["updated_at"] is not None

    def test_soft_delete_contract_dual_channel_verification(
        self, projects_client: ProjectsClient
    ):
        """
        Soft-Delete Contract Verification:
        1. API DELETE returns 204 No Content.
        2. API GET returns 404 Not Found (resource is inaccessible to regular consumers).
        3. Direct SQL asserts the row STILL EXISTS in the database with:
           - is_active = 0
           - deleted_at IS NOT NULL
           - version incremented
        """
        # 1. Create project
        create_res = projects_client.post(
            "/api/v1/sql/projects",
            json={"name": "Soft Delete Target", "key": "SOFTDEL", "lead_email": "soft@atlassian.com"},
        )
        create_res.assert_status_code(201)
        project_id = create_res.json()["id"]

        # 2. Execute DELETE
        del_res = projects_client.delete(f"/api/v1/sql/projects/{project_id}")
        del_res.assert_status_code(204)

        # 3. Channel 1: Public API says 404 Not Found
        get_res = projects_client.get(f"/api/v1/sql/projects/{project_id}")
        get_res.assert_status_code(404)

        # 4. Channel 2: Direct SQL reveals compliance audit row is preserved
        db_row = db_client.get_project_by_id(project_id)
        assert db_row is not None, "Contract Violation: Hard delete occurred instead of soft delete!"
        assert db_row["is_active"] == 0, "Contract Violation: is_active flag must be 0"
        assert db_row["deleted_at"] is not None, "Contract Violation: deleted_at timestamp must be populated"
        assert db_row["version"] == 2, "Contract Violation: version counter must be incremented on deletion"
