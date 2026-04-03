import random

MAX_RETRIES = 3
_BASE = 5      # seconds
_CAP = 300     # 5 min ceiling


def compute_next_retry(attempt: int) -> float:
    delay = min(_CAP, _BASE * (2 ** attempt))
    return delay + random.uniform(0, delay * 0.25)


def should_retry(retry_count: int) -> bool:
    return retry_count < MAX_RETRIES
