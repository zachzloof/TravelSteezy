"""Tests for the rate-limit backoff helper used by the specialist and
Decision-Weigher retry loops.

No API keys and no network: exercises the pure function only, not the async
retry loops themselves (those need a real/mocked ADK Runner, out of scope for
a unit test - the evals suite and the live reproduction that motivated this
fix are the real coverage for the end-to-end behaviour).

    python -m pytest tests/test_runner_backoff.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.runner import _rate_limit_backoff_seconds  # noqa: E402


class _FakeRateLimitError(Exception):
    """Stands in for litellm.exceptions.RateLimitError without importing
    litellm here - only the class name and message text matter to the
    detection logic, not the real exception hierarchy."""


def test_parses_the_apis_own_wait_hint():
    exc = _FakeRateLimitError(
        "Rate limit reached for gpt-4o ... Please try again in 3.094s."
    )
    assert _rate_limit_backoff_seconds(exc, attempt=1) == 3.594


def test_falls_back_to_a_default_when_no_hint_is_present():
    exc = _FakeRateLimitError("Rate limit exceeded, no timing given")
    assert _rate_limit_backoff_seconds(exc, attempt=1) == 2.0
    assert _rate_limit_backoff_seconds(exc, attempt=2) == 4.0


def test_default_backoff_is_capped():
    exc = _FakeRateLimitError("rate_limit_exceeded")
    assert _rate_limit_backoff_seconds(exc, attempt=10) == 10.0


def test_non_rate_limit_errors_get_no_backoff():
    assert _rate_limit_backoff_seconds(RuntimeError("boom"), attempt=1) is None
    assert _rate_limit_backoff_seconds(TimeoutError("timed out"), attempt=1) is None


def test_detects_rate_limit_by_message_even_with_a_generic_exception_type():
    """The exception reaching runner.py may not literally be
    litellm.exceptions.RateLimitError by the time it has passed through
    ADK's own error wrapping - detection also matches on message text so a
    differently-typed wrapper still gets the backoff treatment."""
    exc = Exception("OpenAIException - rate_limit_exceeded for gpt-4o")
    assert _rate_limit_backoff_seconds(exc, attempt=1) is not None
