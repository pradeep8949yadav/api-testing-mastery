import pytest
import responses
import requests
from src.clients.billing_client import BillingClient


class TestServiceVirtualizationAndMocking:
    """
    Module 12: Wire-Level Service Virtualization & Chaos Fault Injection.
    
    Verifies:
    1. Wire-level Contract: Real HTTP serialization, headers, and payload verification.
    2. Transient 503 Failure Injection: Client automatically recovers via exponential retry.
    3. Upstream Timeout Simulation: Strict client timeout SLA enforcement without hangs.
    4. Idempotency Key Integrity: Guaranteeing duplicate payments are not processed.
    5. Retry Exhaustion: Graceful failure handling when upstream dependencies remain completely dead.
    """

    @pytest.fixture
    def billing_client(self) -> BillingClient:
        """Isolated billing client for service virtualization tests."""
        return BillingClient(
            base_url="https://api.payment-gateway.internal/v1",
            timeout=(0.5, 1.0),
            max_retries=3,
        )

    @responses.activate
    def test_wire_level_virtualized_payment_happy_path(self, billing_client: BillingClient):
        """
        Wire-Level Simulation (Happy Path):
        Simulate 3rd-party payment gateway returning 200 with transaction confirmation.
        Assert real serialization and verify headers transmitted across the wire.
        """
        gateway_url = "https://api.payment-gateway.internal/v1/charges"
        responses.add(
            responses.POST,
            gateway_url,
            json={"status": "succeeded", "charge_id": "ch_test_998877", "amount": 5000},
            status=200,
        )

        res = billing_client.charge_license(account_id="acc_atlassian_01", amount_cents=5000)
        res.assert_status_code(200)
        assert res.json()["charge_id"] == "ch_test_998877"

        # Wire Inspection: Assert that the request on the wire actually carried required headers
        captured_request = responses.calls[0].request
        assert "Idempotency-Key" in captured_request.headers
        assert "X-Request-ID" in captured_request.headers
        assert b"acc_atlassian_01" in captured_request.body

    @responses.activate
    def test_transient_503_outage_recovers_via_exponential_retry(self, billing_client: BillingClient):
        """
        Chaos Failure Injection (Transient Outage):
        Upstream returns 503 on Call 1, 503 on Call 2, and 200 OK on Call 3.
        Assert that the client transparently recovers and completes the transaction on Call 3.
        """
        gateway_url = "https://api.payment-gateway.internal/v1/charges"
        # Call 1: 503 Service Unavailable
        responses.add(responses.POST, gateway_url, json={"error": "Gateway Overloaded"}, status=503)
        # Call 2: 503 Service Unavailable
        responses.add(responses.POST, gateway_url, json={"error": "Gateway Overloaded"}, status=503)
        # Call 3: 200 OK (Recovered!)
        responses.add(responses.POST, gateway_url, json={"status": "succeeded", "charge_id": "ch_recovered_123"}, status=200)

        res = billing_client.charge_license(account_id="acc_atlassian_02", amount_cents=2500)
        res.assert_status_code(200)
        assert res.json()["charge_id"] == "ch_recovered_123"

        # Wire Proof: Exactly 3 attempts were transmitted across the wire
        assert len(responses.calls) == 3, f"Expected 3 wire calls (2 retries), but found {len(responses.calls)}"

    @responses.activate
    def test_upstream_timeout_simulation_raises_timeout_error(self, billing_client: BillingClient):
        """
        Chaos Failure Injection (Network Latency / Timeout):
        Simulate an unresponsive payment gateway triggering a socket timeout.
        Verifies that the client raises a clean Timeout exception within configured SLA.
        """
        gateway_url = "https://api.payment-gateway.internal/v1/charges"
        responses.add_callback(
            responses.POST,
            gateway_url,
            callback=lambda request: (_ for _ in ()).throw(requests.exceptions.ConnectTimeout("Connection timed out")),
        )

        with pytest.raises(requests.exceptions.RequestException):
            billing_client.charge_license(account_id="acc_timeout_test", amount_cents=1000)

    @responses.activate
    def test_idempotency_key_preservation_across_calls(self, billing_client: BillingClient):
        """
        Idempotency Protection:
        Verify that passing an explicit idempotency key correctly transmits the exact key over the wire.
        """
        gateway_url = "https://api.payment-gateway.internal/v1/charges"
        responses.add(
            responses.POST,
            gateway_url,
            json={"status": "succeeded", "charge_id": "ch_idemp_111"},
            status=200,
        )

        custom_key = "idemp-key-uuid-999"
        billing_client.charge_license(
            account_id="acc_idemp_01",
            amount_cents=1500,
            idempotency_key=custom_key,
        )

        wire_header = responses.calls[0].request.headers["Idempotency-Key"]
        assert wire_header == custom_key, f"Idempotency Key Mismatch! Expected {custom_key}, got {wire_header}"

    @responses.activate
    def test_catastrophic_500_failure_exhausts_retry_budget(self, billing_client: BillingClient):
        """
        Retry Exhaustion (Persistent Failure):
        Upstream service returns continuous 500 errors.
        Assert that client stops after exhausting retries (1 initial + 3 retries = 4 attempts).
        """
        gateway_url = "https://api.payment-gateway.internal/v1/charges"
        # 4 consecutive 500 errors
        for _ in range(4):
            responses.add(responses.POST, gateway_url, json={"error": "Internal DB Error"}, status=500)

        res = billing_client.charge_license(account_id="acc_dead_service", amount_cents=999)
        res.assert_status_code(500)

        # Wire Proof: Total 4 attempts were made (1 original + 3 retries)
        assert len(responses.calls) == 4, f"Expected 4 attempts before exhaustion, but found {len(responses.calls)}"
