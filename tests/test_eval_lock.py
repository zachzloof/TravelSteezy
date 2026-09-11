"""Tests for the eval-suite concurrency lock.

This exists because two eval-suite processes ran concurrently against the same
SQLite database during development, sharing the same two fixed eval accounts,
and silently corrupted each other's results (one run answered a question about
Reykjavik with details about Chiang Mai, because the other run's setup had
overwritten the shared account's profile mid-turn). See
notes/06-eval-methodology.md for the full story.

These tests exercise the lock directly rather than running the full eval suite,
so they're fast and need no API keys.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.run_evals import ConcurrentRunError, EvalLock  # noqa: E402


@pytest.fixture()
def lock_path():
    tmp = Path(tempfile.mkdtemp(prefix="onward-lock-test-"))
    return tmp / ".eval_lock"


def test_acquire_creates_the_lock_file(lock_path):
    lock = EvalLock(lock_path)
    assert not lock_path.exists()
    lock.acquire()
    assert lock_path.exists()


def test_release_removes_the_lock_file(lock_path):
    lock = EvalLock(lock_path)
    lock.acquire()
    lock.release()
    assert not lock_path.exists()


def test_release_is_safe_to_call_when_nothing_is_held(lock_path):
    """Calling release without a prior acquire (or twice) must not raise."""
    lock = EvalLock(lock_path)
    lock.release()  # nothing to remove
    lock.release()  # still nothing to remove


def test_second_acquire_is_refused_while_the_first_is_held(lock_path):
    """The exact scenario that caused the corruption: two runs, one database."""
    first = EvalLock(lock_path)
    first.acquire()

    second = EvalLock(lock_path)
    with pytest.raises(ConcurrentRunError):
        second.acquire()


def test_acquire_succeeds_again_after_release(lock_path):
    first = EvalLock(lock_path)
    first.acquire()
    first.release()

    second = EvalLock(lock_path)
    second.acquire()  # must not raise - the lock was properly released
    second.release()


def test_error_message_names_the_holding_process(lock_path):
    """The refusal message must be actionable: which PID, when, doing what."""
    import json
    import os

    first = EvalLock(lock_path)
    first.acquire()

    second = EvalLock(lock_path)
    with pytest.raises(ConcurrentRunError) as excinfo:
        second.acquire()

    message = str(excinfo.value)
    recorded = json.loads(lock_path.read_text(encoding="utf-8"))
    assert str(os.getpid()) in message
    assert recorded["pid"] == os.getpid()
    assert str(lock_path) in message
