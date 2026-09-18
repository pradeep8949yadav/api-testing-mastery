from __future__ import annotations
import uuid
from typing import Any, Optional
from src.clients.base_client import BaseClient
from src.clients.api_response import ApiResponse


class BillingClient(BaseClient):
    """
    Enterprise Billing Client communicating with external payment processors (e.g. Stripe / PayPal).
    
    Demonstrates:
    - Wire-level virtualization target.
    - Automatic idempotency key propagation.
    - Resilient retries for transient gateway outages.
    """

    def __init__(
        self,
        base_url: str = "https://api.payment-gateway.internal/v1",
        timeout: tuple[float, float] = (1.0, 3.0),
        max_retries: int = 3,
    ):
        super().__init__(base_url=base_url, timeout=timeout, max_retries=max_retries)

    def charge_license(
        self,
        account_id: str,
        amount_cents: int,
        currency: str = "USD",
        idempotency_key: Optional[str] = None,
        **kwargs: Any,
    ) -> ApiResponse:
        """Execute a license charge against the external payment gateway."""
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        headers = kwargs.pop("headers", {})
        headers["Idempotency-Key"] = idempotency_key

        payload = {
            "account_id": account_id,
            "amount_cents": amount_cents,
            "currency": currency,
        }
        return self.post("/charges", json=payload, headers=headers, **kwargs)
