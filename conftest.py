import pytest
from src.clients.base_client import BaseClient


@pytest.fixture(scope="session")
def api_client():
    """
    Session-scoped BaseClient.
    Initializes a persistent HTTP session with connection pooling and retries.
    Gracefully closes all TCP connections when the test suite execution completes.
    """
    client = BaseClient(base_url="https://httpbin.org", timeout=(3.05, 10.0))
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


def pytest_runtest_makereport(item, call):
    """
    Pytest diagnostic hook.
    When a test fails, this hook can capture diagnostics, latency, or API failure details
    making CI/CD failures instantly debuggable without rerunning.
    """
    if call.excinfo is not None and call.when == "call":
        # Log failure diagnostic
        print(f"\n❌ [FAILURE DIAGNOSTIC] Test '{item.name}' failed in phase '{call.when}'")
