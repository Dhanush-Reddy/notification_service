"""Unit tests for exponential backoff retry logic."""
import pytest
from app.services.retry import compute_next_retry, should_retry, MAX_RETRIES, _BASE_DELAY, _MAX_DELAY


def test_first_retry_in_expected_range():
    # attempt=0: exp=5, jitter up to 25% => [5, 6.25]
    delay = compute_next_retry(0)
    assert _BASE_DELAY <= delay <= _BASE_DELAY * 1.25


def test_second_retry_doubles():
    # attempt=1: exp=10, jitter up to 25% => [10, 12.5]
    delay = compute_next_retry(1)
    assert _BASE_DELAY * 2 <= delay <= _BASE_DELAY * 2 * 1.25


def test_third_retry_doubles_again():
    # attempt=2: exp=20, jitter up to 25% => [20, 25]
    delay = compute_next_retry(2)
    assert _BASE_DELAY * 4 <= delay <= _BASE_DELAY * 4 * 1.25


def test_delay_is_capped_at_max():
    # large attempt number should hit the cap
    delay = compute_next_retry(20)
    assert delay <= _MAX_DELAY * 1.25  # cap + max jitter


def test_should_retry_under_limit():
    assert should_retry(0) is True
    assert should_retry(MAX_RETRIES - 1) is True


def test_should_not_retry_at_limit():
    assert should_retry(MAX_RETRIES) is False


def test_delay_has_variance():
    # two calls with same attempt should not always return identical values (jitter)
    delays = {compute_next_retry(1) for _ in range(20)}
    assert len(delays) > 1, "Expected jitter to produce variance in delay values"
