import socket
import threading
import time
import pytest
import uvicorn
import requests

from src.clients.base_client import BaseClient
from src.clients.projects_client import ProjectsClient
from src.clients.issues_client import IssuesClient
from src.service.app import app


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url():
    """
    Session fixture that spins up the FastAPI Atlassian Mock Server
    in a background thread on a dynamic free port.
    """
    port = _get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    # Wait for server ready
    for _ in range(50):
        try:
            if requests.get(f"{base_url}/health", timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.05)

    yield base_url
    server.should_exit = True


@pytest.fixture(scope="session")
def api_client():
    """Session-scoped BaseClient for external echo tests."""
    client = BaseClient(base_url="https://httpbin.org", timeout=(3.05, 10.0))
    yield client
    client.close()


@pytest.fixture(scope="session")
def projects_client(live_server_url):
    """Session-scoped ProjectsClient connected to live in-memory REST service."""
    client = ProjectsClient(base_url=live_server_url, timeout=(3.05, 10.0))
    yield client
    client.close()


@pytest.fixture(scope="session")
def issues_client():
    """Session-scoped IssuesClient for external echo tests."""
    client = IssuesClient(base_url="https://httpbin.org", timeout=(3.05, 10.0))
    yield client
    client.close()


@pytest.fixture(autouse=True)
def reset_db_state(live_server_url):
    """Autouse fixture resetting database state before each test function."""
    try:
        requests.delete(f"{live_server_url}/api/v1/internal/reset", timeout=2)
    except Exception:
        pass
    yield


@pytest.fixture(scope="function")
def cleanup_tracker(projects_client):
    """Teardown guardian supporting both single ID and typed resource teardowns."""
    created_resources: list[str] = []

    def _track(resource_id: str | None = None, resource_type: str = "projects", **kwargs):
        res_id = resource_id or kwargs.get("resource_id")
        if res_id:
            created_resources.append(res_id)
            return res_id

    yield _track

    for res_id in reversed(created_resources):
        try:
            projects_client.delete_project(res_id)
        except Exception:
            pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        print(f"\n[FAILURE DIAGNOSTIC] Test '{item.name}' failed in phase '{call.when}'")
