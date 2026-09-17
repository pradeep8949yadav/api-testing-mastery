import pytest
from src.clients.projects_client import ProjectsClient
from src.utils.token_factory import (
    create_token,
    create_expired_token,
    create_tampered_token,
    create_refresh_token,
    create_expired_refresh_token,
)



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

    @pytest.mark.parametrize(
        "malformed_header, expected_status, scenario_name",
        [
            ("Bearer null", 401, "Frontend Javascript Null Token"),
            ("Bearer undefined", 401, "Frontend Javascript Undefined Token"),
            ("Basic YWRtaW46cGFzc3dvcmQ=", 401, "Unsupported Basic Auth Scheme"),
            ("Bearer ", 401, "Empty Bearer Token"),
            ("RandomStringWithoutBearer", 401, "Missing Bearer Scheme Prefix"),
        ],
        ids=[
            "NullToken",
            "UndefinedToken",
            "BasicScheme",
            "EmptyToken",
            "MissingBearerPrefix",
        ],
    )
    def test_malformed_authorization_headers_handled_gracefully(
        self,
        projects_client: ProjectsClient,
        malformed_header: str,
        expected_status: int,
        scenario_name: str,
    ):
        """Ensure malformed/bogus auth headers return clean 401s and never crash with 500."""
        res = projects_client.delete(
            "/api/v1/secure/projects/PROJ-100",
            headers={"Authorization": malformed_header},
        )
        res.assert_status_code(expected_status)
        assert res.status_code != 500, f"Critical Bug: Server crashed with 500 on {scenario_name}!"

    def test_token_without_admin_role_rejected_cleanly(
        self, projects_client: ProjectsClient
    ):
        """Token with an unassigned or guest role must be rejected with 403 Forbidden."""
        guest_token = create_token(user_id="guest_user", role="Viewer")
        res = projects_client.delete(
            "/api/v1/secure/projects/PROJ-100",
            headers={"Authorization": f"Bearer {guest_token}"},
        )
        res.assert_status_code(403)
        assert "Forbidden" in res.json()["detail"]

    def test_refresh_token_flow_issues_fresh_access_token(
        self, projects_client: ProjectsClient
    ):
        """Valid refresh token successfully exchanges for a new active access token."""
        valid_refresh_token = create_refresh_token(user_id="usr_admin_1", role="Admin")
        res = projects_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": valid_refresh_token}
        )
        res.assert_status_code(200)
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["role"] == "Admin"

    def test_expired_refresh_token_returns_401(
        self, projects_client: ProjectsClient
    ):
        """Expired refresh token must be rejected with 401 Unauthorized."""
        expired_refresh = create_expired_refresh_token(user_id="usr_admin_1")
        res = projects_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_refresh}
        )
        res.assert_status_code(401)
        assert "expired" in res.json()["detail"].lower()

    def test_access_token_cannot_be_used_as_refresh_token(
        self, projects_client: ProjectsClient
    ):
        """Security: Passing an access token to the refresh endpoint must fail (token type confusion attack)."""
        standard_access_token = create_token(user_id="usr_admin_1", role="Admin")
        res = projects_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": standard_access_token}
        )
        res.assert_status_code(401)
        assert "Invalid token type" in res.json()["detail"]

    def test_client_auto_intercepts_expired_access_token_and_transparently_refreshes(
        self, projects_client: ProjectsClient
    ):
        """
        Enterprise Resilience Test:
        1. Set client with an EXPIRED access token + a VALID refresh token.
        2. Execute an Admin-protected DELETE.
        3. BaseClient interceptor catches 401, calls /api/v1/auth/refresh, acquires new access token, and retries!
        4. Caller receives 204 No Content seamlessly without having to manually refresh!
        """
        # Create target project
        res = projects_client.create_project(
            name="Auto Refresh Intercept Project",
            key="AUTOREF",
            lead_email="sdet@atlassian.com"
        )
        proj_id = res.json()["id"]

        expired_access = create_expired_token(user_id="usr_admin_1", role="Admin")
        valid_refresh = create_refresh_token(user_id="usr_admin_1", role="Admin")

        # Configure client with expired access token and valid refresh token
        projects_client.set_auth_tokens(access_token=expired_access, refresh_token=valid_refresh)

        # Execute DELETE without passing manual headers — client interceptor handles it
        del_res = projects_client.delete(f"/api/v1/secure/projects/{proj_id}")
        del_res.assert_status_code(204)


