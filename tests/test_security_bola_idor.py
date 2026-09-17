import pytest
from src.clients.projects_client import ProjectsClient
from src.utils.token_factory import create_tenant_token


class TestSecurityBolaAndIdor:
    """
    OWASP API Top 10 - Broken Object Level Authorization (BOLA / IDOR) Test Suite.
    
    Verifies:
    1. Cross-tenant data isolation (Tenant Bob cannot READ Tenant Alice's resources).
    2. Cross-tenant integrity protection (Tenant Bob cannot MUTATE Tenant Alice's resources).
    3. Cross-tenant destruction protection (Tenant Bob cannot DELETE Tenant Alice's resources).
    4. Anti-Harvesting / ID Enumeration Defense (Server returns 404 instead of 403 to prevent metadata leak).
    5. Tenant Parameter Spoofing Prevention (Client cannot forge tenant ownership in request payload).
    """

    @pytest.fixture
    def alice_token(self) -> str:
        """Tenant Alice from Org Alpha."""
        return create_tenant_token(user_id="usr_alice_01", tenant_id="org_alpha", role="Developer")

    @pytest.fixture
    def bob_token(self) -> str:
        """Tenant Bob from Org Beta (Attacker in cross-tenant scenarios)."""
        return create_tenant_token(user_id="usr_bob_99", tenant_id="org_beta", role="Developer")

    @pytest.fixture
    def alice_project_id(self, projects_client: ProjectsClient, alice_token: str) -> str:
        """Create a private project owned exclusively by Tenant Alice."""
        res = projects_client.post(
            "/api/v1/tenant/projects",
            json={"name": "Alice Secret Alpha Project", "key": "ALPHASEC", "lead_email": "alice@alpha.org"},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        res.assert_status_code(201)
        return res.json()["id"]

    def test_cross_tenant_read_prevented_returns_404(
        self, projects_client: ProjectsClient, alice_project_id: str, bob_token: str
    ):
        """BOLA Attack: Bob attempts to read Alice's project using his own valid token."""
        res = projects_client.get(
            f"/api/v1/tenant/projects/{alice_project_id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        # 404 ensures zero metadata leakage (Bob cannot determine if project ID exists)
        res.assert_status_code(404)
        assert "not found" in res.json()["detail"].lower()

    def test_cross_tenant_tamper_mutation_prevented_returns_404(
        self, projects_client: ProjectsClient, alice_project_id: str, bob_token: str
    ):
        """BOLA Attack: Bob attempts to update Alice's project name and lead email."""
        res = projects_client.patch(
            f"/api/v1/tenant/projects/{alice_project_id}",
            json={"name": "Hacked by Bob", "lead_email": "bob@hacker.com"},
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        res.assert_status_code(404)
        assert "not found" in res.json()["detail"].lower()

    def test_cross_tenant_deletion_prevented_returns_404(
        self, projects_client: ProjectsClient, alice_project_id: str, bob_token: str
    ):
        """BOLA Attack: Bob attempts to delete Alice's project."""
        res = projects_client.delete(
            f"/api/v1/tenant/projects/{alice_project_id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        res.assert_status_code(404)

    def test_tenant_parameter_spoofing_prevented(
        self, projects_client: ProjectsClient, bob_token: str, alice_token: str
    ):
        """
        Security Defense:
        Bob sends 'tenant_id': 'org_alpha' in creation body trying to claim Alice's org.
        Server must ignore the body field and strictly use the cryptographically signed JWT claim.
        """
        res = projects_client.post(
            "/api/v1/tenant/projects",
            json={
                "name": "Spoof Attempt Project",
                "key": "SPOOF",
                "lead_email": "attacker@beta.org",
                "tenant_id": "org_alpha",  # Injected forge attempt
            },
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        res.assert_status_code(201)
        data = res.json()
        assert data["tenant_id"] == "org_beta", "Security Flaw: Server accepted client-supplied tenant_id!"

    def test_legitimate_tenant_full_lifecycle_succeeds(
        self, projects_client: ProjectsClient, alice_token: str
    ):
        """Happy Path: Alice can create, read, update, and delete her own project seamlessly."""
        # 1. Create
        create_res = projects_client.post(
            "/api/v1/tenant/projects",
            json={"name": "Alice Legitimate Project", "key": "ALICEOK", "lead_email": "alice@alpha.org"},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        create_res.assert_status_code(201)
        proj_id = create_res.json()["id"]

        # 2. Read
        get_res = projects_client.get(
            f"/api/v1/tenant/projects/{proj_id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        get_res.assert_status_code(200)
        assert get_res.json()["name"] == "Alice Legitimate Project"

        # 3. Patch
        patch_res = projects_client.patch(
            f"/api/v1/tenant/projects/{proj_id}",
            json={"name": "Alice Renamed Project"},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        patch_res.assert_status_code(200)
        assert patch_res.json()["name"] == "Alice Renamed Project"

        # 4. Delete
        del_res = projects_client.delete(
            f"/api/v1/tenant/projects/{proj_id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        del_res.assert_status_code(204)
