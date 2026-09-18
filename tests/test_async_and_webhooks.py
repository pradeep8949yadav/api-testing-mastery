import pytest
import hmac
import hashlib
import json
from src.clients.projects_client import ProjectsClient
from src.utils.async_poller import (
    poll_until_complete,
    AsyncPollingTimeoutError,
    AsyncJobFailedError,
)
from src.service.app import WEBHOOK_SHARED_SECRET


class TestAsyncApisAndWebhooks:
    """
    Module 13: Asynchronous APIs, Smart Polling & Webhooks Test Suite.
    
    Verifies:
    1. HTTP 202 Accepted Contract: Location & Retry-After headers.
    2. Smart Polling Lifecycle: Dynamic state tracking to COMPLETED with download artifact.
    3. Fast-Fail Safety: Immediate termination on terminal failure states (FAILED).
    4. SLA Timeout Enforcement: Wall-clock deadline prevents hanging CI pipelines.
    5. Webhook HMAC-SHA256 Security: Cryptographic payload verification and tamper detection.
    """

    def test_202_accepted_and_smart_polling_happy_path(
        self, projects_client: ProjectsClient
    ):
        """
        Pattern A (Happy Path):
        1. POST /jobs/export returns 202 Accepted + Location header.
        2. AsyncPoller repeatedly polls the Location endpoint.
        3. Job successfully transitions from QUEUED -> PROCESSING -> COMPLETED.
        """
        # 1. Initiate asynchronous background job
        init_res = projects_client.post(
            "/api/v1/jobs/export",
            json={"job_type": "issues_csv"},
        )
        init_res.assert_status_code(202)
        
        # Verify 202 Contract Headers
        location_header = init_res.headers.get("Location")
        assert location_header is not None, "202 Accepted Contract Violation: Location header missing!"
        assert "Retry-After" in init_res.headers

        job_id = init_res.json()["job_id"]

        # 2. Smart Poller with backoff & deadline
        final_res = poll_until_complete(
            poll_fn=lambda: projects_client.get(location_header),
            success_status="COMPLETED",
            max_duration_sec=5.0,
            initial_interval=0.05,
        )

        final_data = final_res.json()
        assert final_data["status"] == "COMPLETED"
        assert final_data["progress_pct"] == 100
        assert "download_url" in final_data
        assert job_id in final_data["download_url"]

    def test_async_job_fast_fails_on_terminal_error(
        self, projects_client: ProjectsClient
    ):
        """
        Resilience Guard (Fail-Fast):
        When a background job encounters an unrecoverable failure (status == FAILED),
        the poller must halt immediately and raise AsyncJobFailedError instead of waiting for timeout.
        """
        init_res = projects_client.post(
            "/api/v1/jobs/export",
            json={"job_type": "issues_csv", "fail_intentionally": True},
        )
        init_res.assert_status_code(202)
        location = init_res.headers["Location"]

        # Poller must fail fast with diagnostic information
        with pytest.raises(AsyncJobFailedError) as exc_info:
            poll_until_complete(
                poll_fn=lambda: projects_client.get(location),
                success_status="COMPLETED",
                failure_statuses=("FAILED", "ERROR"),
                max_duration_sec=5.0,
                initial_interval=0.05,
            )

        assert "FAILED" in str(exc_info.value)
        assert "Worker process terminated unexpectedly" in str(exc_info.value)

    def test_async_polling_deadline_enforces_timeout_sla(
        self, projects_client: ProjectsClient
    ):
        """
        Safety Boundary:
        A stuck job (infinite processing) must trigger AsyncPollingTimeoutError
        strictly within the specified SLA deadline (e.g. 0.4 seconds).
        """
        init_res = projects_client.post(
            "/api/v1/jobs/export",
            json={"job_type": "issues_csv", "never_finish": True},
        )
        location = init_res.headers["Location"]

        with pytest.raises(AsyncPollingTimeoutError) as exc_info:
            poll_until_complete(
                poll_fn=lambda: projects_client.get(location),
                success_status="COMPLETED",
                max_duration_sec=0.4,
                initial_interval=0.05,
            )

        assert "Timeout" in str(exc_info.value) or "Maximum Polling Attempts" in str(exc_info.value)


    def test_webhook_hmac_signature_verification_success(
        self, projects_client: ProjectsClient
    ):
        """
        Pattern B (Webhook Ingestion Security):
        Valid webhook payload signed with shared secret using HMAC-SHA256 must be accepted (200).
        """
        payload = {
            "event": "issue.created",
            "issue_key": "PROJ-101",
            "timestamp": 1773760000,
        }
        raw_bytes = json.dumps(payload).encode("utf-8")

        # Generate legitimate cryptographic signature
        expected_sig = hmac.new(
            WEBHOOK_SHARED_SECRET.encode("utf-8"),
            raw_bytes,
            hashlib.sha256,
        ).hexdigest()

        res = projects_client.post(
            "/api/v1/webhooks/listener",
            data=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={expected_sig}",
            },
        )
        res.assert_status_code(200)
        assert res.json()["status"] == "event_acknowledged"

    def test_webhook_tampered_signature_rejected_with_401(
        self, projects_client: ProjectsClient
    ):
        """
        Webhook Security Defense:
        Payload signed with rogue key or forged signature must be rejected with 401 Unauthorized.
        """
        payload = {"event": "issue.deleted", "issue_key": "PROJ-999"}
        raw_bytes = json.dumps(payload).encode("utf-8")

        res = projects_client.post(
            "/api/v1/webhooks/listener",
            data=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=forged_attacker_hmac_signature_hash_value_12345",
            },
        )
        res.assert_status_code(401)
        assert "signature verification failed" in res.json()["detail"].lower()
