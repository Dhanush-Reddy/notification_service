import random
import logging

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_BASE_DELAY = 5      # seconds
_MAX_DELAY = 300     # cap at 5 minutes


def compute_next_retry(attempt: int) -> float:
    """Exponential backoff with ±25% jitter.

    attempt is 0-indexed — so first retry uses attempt=0.
    Returns delay in seconds before next attempt.
    """
    exp = min(_MAX_DELAY, _BASE_DELAY * (2 ** attempt))
    jitter = random.uniform(0, exp * 0.25)
    return exp + jitter


def should_retry(retry_count: int) -> bool:
    return retry_count < MAX_RETRIES
