import pytest
from app.services.retry import compute_next_retry, should_retry, MAX_RETRIES

_BASE = 5
_CAP = 300


def test_first_retry_in_expected_range():
    delay = compute_next_retry(0)
    assert _BASE <= delay <= _BASE * 1.25


def test_second_retry_doubles():
    delay = compute_next_retry(1)
    assert _BASE * 2 <= delay <= _BASE * 2 * 1.25


def test_third_retry_doubles_again():
    delay = compute_next_retry(2)
    assert _BASE * 4 <= delay <= _BASE * 4 * 1.25


def test_delay_is_capped_at_max():
    delay = compute_next_retry(20)
    assert delay <= _CAP * 1.25


def test_should_retry_under_limit():
    assert should_retry(0) is True
    assert should_retry(MAX_RETRIES - 1) is True


def test_should_not_retry_at_limit():
    assert should_retry(MAX_RETRIES) is False


def test_delay_has_variance():
    delays = {compute_next_retry(1) for _ in range(20)}
    assert len(delays) > 1
