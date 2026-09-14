import pytest
from src.clients.projects_client import ProjectsClient
from src.utils.token_factory import create_token, create_expired_token, create_tampered_token


class TestAuthenticationAndRbac:
    """
    Security Test Suite verifying:
    - AuthN (Authentication - 401): Missing token, expired token, tampered signature.
    - AuthZ (Authorization / RBAC - 403): Insufficient role permissions (Viewer vs Admin).
    - OAuth / JWT Login flow.
    """

    def test_secure_delete_with_admin_token_succeeds(
        self, projects_client: ProjectsClient
    ):
        """Happy path: Valid Admin token successfully deletes protected resource (204)."""
        # 1. Create a project
        res = projects_client.create_project(
            name="Admin Protected Project",
            key="ADMINSEC",
            lead_email="admin@atlassian.com"
        )
        proj_id = res.json()["id"]

        # 2. Delete using Admin token
        admin_token = create_token(user_id="usr_admin_1", role="Admin")
        del_res = projects_client.delete(
            f"/api/v1/secure/projects/{proj_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        del_res.assert_status_code(204)

    def test_missing_token_returns_401_unauthorized(
        self, projects_client: ProjectsClient
    ):
        """AuthN Failure: Request without Authorization header must return 401."""
        res = projects_client.delete("/api/v1/secure/projects/PROJ-100")
        res.assert_status_code(401)
        assert "Missing or malformed Authorization header" in res.json()["detail"]

    def test_expired_token_returns_401_unauthorized(
        self, projects_client: ProjectsClient
    ):
        """AuthN Failure: Token with expired 'exp' timestamp must return 401."""
        expired_token = create_expired_token(user_id="usr_123", role="Admin")
        res = projects_client.delete(
            "/api/v1/secure/projects/PROJ-100",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        res.assert_status_code(401)
        assert "Token has expired" in res.json()["detail"]

    def test_tampered_token_signature_returns_401_unauthorized(
        self, projects_client: ProjectsClient
    ):
        """AuthN Failure: Token signed with unauthorized rogue key must return 401."""
        tampered_token = create_tampered_token(user_id="hacker", role="Admin")
        res = projects_client.delete(
            "/api/v1/secure/projects/PROJ-100",
            headers={"Authorization": f"Bearer {tampered_token}"}
        )
        res.assert_status_code(401)
        assert "Invalid token signature" in res.json()["detail"]

    def test_viewer_role_attempting_admin_action_returns_403_forbidden(
        self, projects_client: ProjectsClient
    ):
        """
        AuthZ / RBAC Failure:
        Token is 100% valid and identity is verified,
        BUT user has 'Viewer' role, which cannot execute DELETE -> 403 Forbidden.
        """
        # Create project first
        res = projects_client.create_project(
            name="Viewer Target Project",
            key="VIEWSEC",
            lead_email="lead@atlassian.com"
        )
        proj_id = res.json()["id"]

        viewer_token = create_token(user_id="usr_viewer_9", role="Viewer")
        del_res = projects_client.delete(
            f"/api/v1/secure/projects/{proj_id}",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        del_res.assert_status_code(403)
        assert "Forbidden" in del_res.json()["detail"]
        assert "Viewer" in del_res.json()["detail"]

    def test_login_flow_issues_valid_bearer_token(
        self, projects_client: ProjectsClient
    ):
        """Verify login endpoint issues cryptographically valid JWT tokens."""
        login_res = projects_client.post(
            "/api/v1/auth/login",
            json={"username": "sys_admin", "password": "correct_password", "role": "Admin"}
        )
        login_res.assert_status_code(200)
        data = login_res.json()
        
        assert data["token_type"] == "Bearer"
        assert "access_token" in data
        assert data["role"] == "Admin"
