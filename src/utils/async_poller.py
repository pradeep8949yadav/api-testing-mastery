from __future__ import annotations
import time
from typing import Callable, Any, Sequence, Optional
from src.clients.api_response import ApiResponse


class AsyncPollingTimeoutError(TimeoutError):
    """Raised when an asynchronous operation exceeds the maximum allowable polling SLA."""
    pass


class AsyncJobFailedError(AssertionError):
    """Raised immediately when an asynchronous job transitions to a terminal failure state."""
    pass


def poll_until_complete(
    poll_fn: Callable[[], ApiResponse],
    status_extractor: Callable[[ApiResponse], str] = lambda res: res.json().get("status", ""),
    success_status: str = "COMPLETED",
    failure_statuses: Sequence[str] = ("FAILED", "CANCELLED", "ERROR", "REJECTED"),
    max_duration_sec: float = 10.0,
    max_attempts: int = 15,
    initial_interval: float = 0.1,
    backoff_factor: float = 1.3,
    max_interval: float = 1.0,
) -> ApiResponse:
    """
    Enterprise Asynchronous Polling Guardian.
    
    Safety Guarantees:
    1. Hard SLA Wall-Clock Deadline: Raises AsyncPollingTimeoutError if job doesn't finish in time.
    2. Attempt Ceiling: Prevents infinite loops if clocks skew.
    3. Fast-Fail Terminal States: Instantly halts and raises AsyncJobFailedError if status is FAILED.
    4. Adaptive Backoff: Respects server 'Retry-After' headers when present.
    """
    start_time = time.monotonic()
    current_interval = initial_interval
    attempt = 0

    while True:
        attempt += 1
        elapsed = time.monotonic() - start_time

        # 1. Hard Deadline SLA Guard
        if elapsed > max_duration_sec:
            raise AsyncPollingTimeoutError(
                f"Asynchronous Polling Timeout Exceeded!\n"
                f"  Max Allowed : {max_duration_sec:.1f}s\n"
                f"  Elapsed     : {elapsed:.2f}s\n"
                f"  Attempts    : {attempt}\n"
                f"  Target State: {success_status}"
            )

        # 2. Maximum Attempts Guard
        if attempt > max_attempts:
            raise AsyncPollingTimeoutError(
                f"Maximum Polling Attempts ({max_attempts}) reached before job achieved '{success_status}'!"
            )

        # 3. Execute Poll
        response = poll_fn()
        current_status = status_extractor(response)

        # 4. Success Termination
        if current_status == success_status:
            return response

        # 5. Fast-Fail Terminal Error Detection
        if current_status in failure_statuses:
            error_details = response.json().get("error", "No additional error message provided.")
            raise AsyncJobFailedError(
                f"Asynchronous Job Failed Fast!\n"
                f"  Terminal Status : {current_status}\n"
                f"  Error Details   : {error_details}\n"
                f"  Attempts Made   : {attempt}\n"
                f"  Elapsed Time    : {elapsed:.2f}s"
            )

        # 6. Compute Sleep Interval (Honoring Retry-After Header if present)
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            sleep_duration = min(float(retry_after), max_interval)
        else:
            sleep_duration = current_interval

        time.sleep(sleep_duration)
        current_interval = min(current_interval * backoff_factor, max_interval)
