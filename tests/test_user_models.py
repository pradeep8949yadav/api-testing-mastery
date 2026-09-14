import pytest
from pydantic import ValidationError
from src.models.user import UserCreate, UserResponse


class TestUserModelsAndContracts:
    """Test suite demonstrating local client validation and contract validation."""

    def test_valid_user_creation_and_serialization(self):
        """Verify that valid inputs produce a properly formatted payload dictionary."""
        user = UserCreate(
            email="Pradeep.Yadav@atlassian.com",
            role="Developer",
            age=26
        )
        payload = user.model_dump()

        # Email validator lowercases automatically
        assert payload["email"] == "pradeep.yadav@atlassian.com"
        assert payload["role"] == "Developer"
        assert payload["age"] == 26
        # Default value applied
        assert payload["department"] == "Engineering"

    def test_local_validation_fails_on_underage(self):
        """Verify that invalid input fails locally before ever touching the network."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="intern@atlassian.com",
                role="Reporter",
                age=15  # Violates ge=18 boundary
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("age",) for e in errors)
        assert "greater than or equal to 18" in str(exc_info.value)

    def test_local_validation_fails_on_unauthorized_role(self):
        """Verify Literal validation catches unsupported roles locally."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="hacker@atlassian.com",
                role="SuperAdmin",  # Not in ("Admin", "Developer", "Reporter")
                age=30
            )

        assert "Input should be 'Admin', 'Developer' or 'Reporter'" in str(exc_info.value)

    def test_contract_compliance_success(self):
        """Verify response from backend matches our expected schema contract."""
        backend_response = {
            "id": "usr_991",
            "email": "lead@atlassian.com",
            "role": "Admin",
            "is_active": True,
            "department": "Infrastructure"
        }
        # Validate against schema
        user_model = UserResponse.model_validate(backend_response)
        
        assert user_model.id == "usr_991"
        assert user_model.role == "Admin"
        assert user_model.is_active is True

    def test_contract_breaking_change_detected_immediately(self):
        """
        Simulate a backend breaking change:
        Backend developer renamed 'department' to 'team_name'.
        Pydantic must catch this contract violation immediately!
        """
        breaking_backend_response = {
            "id": "usr_991",
            "email": "lead@atlassian.com",
            "role": "Admin",
            "is_active": True,
            "team_name": "Infrastructure"  # 'department' is missing!
        }

        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(breaking_backend_response)

        # Immediate contract violation diagnostic
        assert "department" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)
