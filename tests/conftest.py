"""Suite-wide safety: the tests never talk to the live Langfuse project.

Without this, running `pytest` on a machine that has a real `.env` writes a
trace to the production Langfuse project for every turn the suite drives -
`run_turn` opens a `Trace` before any agent is stubbed, so stubbing the agents
is not enough. Noticed while watching a live project during a test run: eval
traces and test traces interleaved, with test messages ("Laos or Cambodia
next?") sitting in the real project's timeline.

Patching the env vars is not sufficient either. `backend.tracing.langfuse_setup`
binds `settings` by value at import time, so the per-test fixtures that reload
`backend.config` produce a fresh Settings instance the tracing module never
sees - the same trap `test_touching_last_active_survives_the_llm_disabled_path`
documents for `openai_api_key`. The keys are therefore blanked on the instance
the tracing module actually holds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _no_live_tracing(monkeypatch):
    from backend.tracing import langfuse_setup

    # Blanking the keys is the obvious move and is not enough on its own: the
    # per-test fixtures reload backend.config, and which Settings instance
    # langfuse_setup ends up holding after that depends on import order, so the
    # patch held for some test files and not others in a full-suite run.
    # _client() is the single choke point every Trace and every span goes
    # through, so closing it is order-independent.
    monkeypatch.setattr(langfuse_setup, "_client", lambda: None)
    monkeypatch.setattr(langfuse_setup.settings, "langfuse_public_key", None, raising=False)
    monkeypatch.setattr(langfuse_setup.settings, "langfuse_secret_key", None, raising=False)
