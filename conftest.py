import pytest
from src.clients.base_client import BaseClient


@pytest.fixture(scope="session")
def api_client():
    """Session-scoped BaseClient."""
    client = BaseClient(base_url="https://httpbin.org", timeout=(3.05, 10.0))
    yield client
    client.close()


@pytest.fixture(scope="session")
def projects_client():
    """Session-scoped ProjectsClient."""
    from src.clients.projects_client import ProjectsClient
    client = ProjectsClient(base_url="https://httpbin.org", timeout=(3.05, 10.0))
    yield client
    client.close()


@pytest.fixture(scope="session")
def issues_client():
    """Session-scoped IssuesClient."""
    from src.clients.issues_client import IssuesClient
    client = IssuesClient(base_url="https://httpbin.org", timeout=(3.05, 10.0))
    yield client
    client.close()


@pytest.fixture(scope="function")
def cleanup_tracker(api_client):
    """
    Production-grade Teardown Guardian.
    Tracks resource IDs created during a test.
    Guarantees cleanup/deletion in reverse order after test completes,
    even if assertions fail in the middle of a test.
    """
    created_resources: list[tuple[str, str]] = []  # List of (resource_type, id)

    def _track(resource_type: str, resource_id: str):
        created_resources.append((resource_type, resource_id))
        return resource_id

    yield _track

    # TEARDOWN: Clean up all tracked resources
    for resource_type, resource_id in reversed(created_resources):
        try:
            api_client.delete(f"/{resource_type}/{resource_id}")
        except Exception as e:
            print(f"\n[Teardown Warning] Failed to delete {resource_type}/{resource_id}: {e}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Pytest diagnostic hook wrapper.
    Safely logs test failures using ASCII characters compatible with Windows cp1252.
    """
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        print(f"\n[FAILURE DIAGNOSTIC] Test '{item.name}' failed in phase '{call.when}'")
