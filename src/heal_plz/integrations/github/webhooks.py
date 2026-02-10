import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_signature(
    payload: bytes, signature: Optional[str], secret: str
) -> bool:
    if not signature or not secret:
        return not secret  # if no secret configured, skip verification
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


HANDLED_EVENTS = {
    "workflow_run",
    "check_run",
    "check_suite",
    "pull_request",
}


def is_handled_event(event_type: str) -> bool:
    return event_type in HANDLED_EVENTS
