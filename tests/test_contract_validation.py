import pytest
import jsonschema
from src.clients.projects_client import ProjectsClient
from src.utils.schema_validator import validate_contract


class TestContractValidation:
    """
    Contract Testing Suite using JSON Schema Draft-07.
    Ensures backend responses adhere strictly to API specifications,
    protecting mobile apps, SPAs, and third-party consumers from breaking changes.
    """

    def test_live_project_creation_conforms_to_schema(self, projects_client: ProjectsClient):
        """Verify POST /api/v1/projects response matches project_schema.json exactly."""
        response = projects_client.create_project(
            name="Contract Compliance Project",
            key="SCHEMA",
            lead_email="architect@atlassian.com",
            description="Testing contract adherence"
        )
        response.assert_status_code(201)
        
        # Validate against JSON Schema
        validate_contract(response.json(), "project_schema.json")

    def test_live_project_get_conforms_to_schema(self, projects_client: ProjectsClient):
        """Verify GET /api/v1/projects/{id} response matches project_schema.json."""
        # Create first
        create_res = projects_client.create_project(
            name="Fetch Contract Project",
            key="FETCH",
            lead_email="fetch@atlassian.com"
        )
        create_res.assert_status_code(201)
        proj_id = create_res.json()["id"]

        # Fetch and validate
        get_res = projects_client.get_project(proj_id)
        get_res.assert_status_code(200)
        validate_contract(get_res.json(), "project_schema.json")

    def test_contract_violation_on_missing_required_field(self):
        """Verify schema validator detects missing required fields (breaking change)."""
        breaking_payload = {
            "id": "PROJ-101",
            "name": "Missing Key Project",
            # "key" is omitted!
            "lead_email": "test@atlassian.com",
            "description": None
        }

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            validate_contract(breaking_payload, "project_schema.json")

        assert "'key' is a required property" in str(exc_info.value)

    def test_contract_violation_on_type_mismatch(self):
        """Verify schema validator detects data type mutation (e.g. string to int)."""
        breaking_payload = {
            "id": 101,  # Broke contract: expected string matching '^PROJ-[0-9]+$'
            "name": "Type Mismatch Project",
            "key": "TYPE",
            "lead_email": "test@atlassian.com",
            "description": None
        }

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            validate_contract(breaking_payload, "project_schema.json")

        assert "101 is not of type 'string'" in str(exc_info.value)

    def test_contract_violation_on_unexpected_additional_property(self):
        """Verify additionalProperties: false catches unauthorized field additions."""
        breaking_payload = {
            "id": "PROJ-102",
            "name": "Extra Field Project",
            "key": "EXTRA",
            "lead_email": "test@atlassian.com",
            "description": None,
            "secret_internal_token": "UNAUTHORIZED_FIELD"  # Not allowed in contract!
        }

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            validate_contract(breaking_payload, "project_schema.json")

        assert "Additional properties are not allowed" in str(exc_info.value)
