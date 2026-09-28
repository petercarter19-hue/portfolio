"""One request deadline and bounded capacity, including abandoned work."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from threading import BoundedSemaphore
from time import monotonic

from services.ai_foundation.errors import ProviderUnavailableError

REQUEST_TIMEOUT_SECONDS = 20.0
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ask-pete")
_SLOTS = BoundedSemaphore(2)


class AskPeteDeadlineError(ProviderUnavailableError):
    """Fixed operational reason; retains the existing provider failure contract."""
    def __init__(self, reason):
        if reason not in {"deadline_exceeded", "capacity_occupied"}:
            raise ValueError("invalid deadline reason")
        self.reason = reason
        super().__init__("Ask Pete request deadline exceeded" if reason == "deadline_exceeded"
                         else "Ask Pete capacity is occupied")


@dataclass(frozen=True)
class RequestDeadline:
    expires_at: float

    @classmethod
    def start(cls, seconds: float = REQUEST_TIMEOUT_SECONDS):
        if not 0 < seconds <= REQUEST_TIMEOUT_SECONDS:
            raise ValueError("invalid Ask Pete deadline")
        return cls(monotonic() + seconds)

    def remaining(self) -> float:
        remaining = self.expires_at - monotonic()
        if remaining <= 0:
            raise AskPeteDeadlineError("deadline_exceeded")
        return remaining


def run_bounded(callback, deadline: RequestDeadline):
    deadline.remaining()
    slots = _SLOTS
    if not slots.acquire(blocking=False):
        raise AskPeteDeadlineError("capacity_occupied")
    try:
        future = _POOL.submit(callback)
    except BaseException:
        slots.release()
        raise
    # A timeout cannot make a still-running socket/token acquisition free.
    # Hold the slot until the work actually ends; never queue more work behind it.
    future.add_done_callback(lambda _future: slots.release())
    try:
        result = future.result(timeout=deadline.remaining())
    except TimeoutError as error:
        raise AskPeteDeadlineError("deadline_exceeded") from error
    deadline.remaining()
    return result
