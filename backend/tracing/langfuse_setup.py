"""Langfuse tracing (SDK v4, OpenTelemetry-based).

Two layers, deliberately different in how they get captured:

1. AUTOMATIC. google-adk and openai are instrumented once at process startup
   (``init_tracing()``, called from backend/main.py's lifespan) via
   OpenInference's OTEL instrumentors. From that point on, EVERY ADK
   ``Runner.run_async()`` call anywhere in this app - every specialist,
   turn_parser, decision_weigher, concierge, local_guide, discovery_agent, the
   onboarding extractor - and every raw OpenAI completion
   (backend/rag/live_lookup.py) is captured with zero tracing code at the call
   site: the real model name, real token usage, the actual request/response,
   and (for ADK) the correct chain -> agent -> generation/tool tree - because
   that IS the officially documented, recommended way to trace a Google ADK
   app with Langfuse. See notes/09-observability-and-tracing.md.

   This replaced an earlier hand-rolled version that manually parsed ADK's
   event stream (pairing function-call/function-response events by id,
   summing usage_metadata) and wrapped every agent call in a manually-typed
   span or generation. That version worked, but it was reinventing - less
   completely - what this instrumentation already does for free: it never
   captured the actual request/response bodies, and it had no way to produce
   the ``agent``/``tool``/``chain`` observation types at all (those plus
   ``retriever``/``evaluator``/``embedding``/``guardrail`` require SDK
   >=3.3.1; this app was pinned to a much older v2 SDK that only had
   span/generation/event, with no documented reason for the pin).

2. MANUAL, for the few things that are neither an ADK call nor an OpenAI call:
   the root span for one whole turn (so everything above lands under ONE
   trace instead of a fresh one per agent call), and the two purely-Python
   orchestration steps - memory read/write, and the ``asyncio.gather``
   fan-out wrapper itself.

When Langfuse keys are absent, every object here becomes a no-op with the
same interface, so tracing can never take down a chat turn and the app runs
fine without the service. Trace ids are generated locally either way, which
is what lets an eval run be tagged and correlated even in offline mode.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import ExitStack, contextmanager
from functools import lru_cache
from typing import Any, Iterator

from backend.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client():
    if not settings.langfuse_enabled:
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse disabled: could not initialise client (%s)", exc)
        return None


@lru_cache(maxsize=1)
def _instrumented() -> bool:
    """Turn on OTEL auto-instrumentation for google-adk and openai.

    ``lru_cache`` makes this idempotent, so ``init_tracing()`` can be called
    more than once (e.g. once from the app lifespan, once from an eval
    script) without double-instrumenting.
    """
    if _client() is None:
        return False
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        from openinference.instrumentation.openai import OpenAIInstrumentor

        GoogleADKInstrumentor().instrument()
        OpenAIInstrumentor().instrument()
        logger.info("Langfuse: google-adk + openai auto-instrumentation enabled")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse auto-instrumentation failed: %s", exc)
        return False


def init_tracing() -> None:
    """Call once at process startup (see backend/main.py's lifespan)."""
    _instrumented()


def tracing_enabled() -> bool:
    return _client() is not None


class _NoOpObservation:
    """Same surface as a Langfuse v4 observation, does nothing."""

    def update(self, **_: Any) -> "_NoOpObservation":
        return self


class Trace:
    """One user turn (or one onboarding step). Wraps a Langfuse v4 root
    observation for it, or nothing at all.

    Everything ADK or OpenAI does during the turn is captured automatically
    (see module docstring) as long as it happens while this Trace is open.
    OpenTelemetry propagates the "current span" through contextvars, which
    survives await points and ``asyncio.gather`` (each gathered coroutine is
    wrapped in a Task that copies the context at creation time) - so, unlike
    the old hand-rolled tracer, nothing here needs an explicit ``parent=``
    handle threaded through the fan-out for correct nesting.
    """

    def __init__(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        input: Any = None,
    ) -> None:
        self.name = name
        # Recorded locally regardless of Langfuse, so /chat can always return
        # a per-agent timing breakdown for the demo panel - independent of,
        # and a cross-check against, whatever Langfuse itself captured.
        self.spans: list[dict[str, Any]] = []
        self._stack = ExitStack()
        self._observation: Any = None
        self._ended = False
        self.id = str(uuid.uuid4())

        client = _client()
        if client is not None:
            try:
                from langfuse import propagate_attributes

                self._stack.enter_context(
                    propagate_attributes(
                        trace_name=name,
                        user_id=user_id,
                        session_id=session_id,
                        tags=tags,
                        metadata=metadata,
                    )
                )
                self._observation = self._stack.enter_context(
                    client.start_as_current_observation(name=name, as_type="span", input=input)
                )
                self.id = client.get_current_trace_id() or self.id
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse trace creation failed: %s", exc)
                self._observation = None
                self._stack.close()
                self._stack = ExitStack()

    @contextmanager
    def span(
        self, name: str, input: Any = None, metadata: dict[str, Any] | None = None
    ) -> Iterator[Any]:
        """A real Langfuse span for a step that is NOT an ADK or OpenAI call
        (those are captured automatically - see module docstring): memory
        read/write, the asyncio.gather fan-out wrapper.
        """
        started = time.perf_counter()
        record: dict[str, Any] = {"name": name, "status": "ok", "summary": None}
        client = _client()
        cm = None
        handle: Any = _NoOpObservation()
        if client is not None:
            try:
                cm = client.start_as_current_observation(
                    name=name, as_type="span", input=input, metadata=metadata
                )
                handle = cm.__enter__()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse span creation failed: %s", exc)
                cm = None
        try:
            yield handle
        except Exception as exc:
            record["status"] = "error"
            record["summary"] = f"{type(exc).__name__}: {exc}"
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.spans.append(record)
            if cm is not None:
                try:
                    handle.update(level="ERROR", status_message=str(exc))
                except Exception:  # noqa: BLE001
                    pass
                try:
                    cm.__exit__(type(exc), exc, exc.__traceback__)
                except Exception:  # noqa: BLE001
                    pass
            raise
        else:
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.spans.append(record)
            if cm is not None:
                try:
                    cm.__exit__(None, None, None)
                except Exception:  # noqa: BLE001
                    pass

    @contextmanager
    def local_step(self, name: str) -> Iterator[dict[str, Any]]:
        """Local-only timing for the app's own "what ran" panel, for a step
        whose real tracing detail is already captured elsewhere - an ADK
        agent call, auto-instrumented per the module docstring - and only
        needs a wall-clock entry in this app's own UI, not a second Langfuse
        observation duplicating what the instrumentor already recorded.
        """
        started = time.perf_counter()
        record: dict[str, Any] = {"name": name, "status": "ok", "summary": None}
        try:
            yield record
        except Exception as exc:
            record["status"] = "error"
            record["summary"] = f"{type(exc).__name__}: {exc}"
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.spans.append(record)
            raise
        else:
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.spans.append(record)

    def note(self, name: str, summary: str, status: str = "ok", duration_ms: int | None = None) -> None:
        """Record a span that was not timed inline (e.g. a skipped agent)."""
        self.spans.append(
            {"name": name, "status": status, "summary": summary, "duration_ms": duration_ms}
        )

    def set_span_status(self, name: str, status: str, summary: str | None = None) -> None:
        for record in reversed(self.spans):
            if record["name"] == name:
                record["status"] = status
                if summary:
                    record["summary"] = summary
                return

    def set_span_summary(self, name: str, summary: str) -> None:
        for record in reversed(self.spans):
            if record["name"] == name:
                record["summary"] = summary
                return

    def end(self, output: Any = None, metadata: dict[str, Any] | None = None) -> None:
        """Close the root observation. Idempotent - safe to call more than
        once (e.g. an explicit call with the real output on every normal
        return path, plus an unconditional safety-net call in the caller's
        ``finally``, for the rare uncaught-exception path where nothing else
        would close it). Only the first call's output is kept.
        """
        if self._ended:
            return
        self._ended = True
        if self._observation is not None:
            try:
                self._observation.update(output=output, metadata=metadata)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse trace update failed: %s", exc)
        try:
            self._stack.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse trace close failed: %s", exc)

    @property
    def url(self) -> str | None:
        client = _client()
        if client is None:
            return None
        try:
            return client.get_trace_url(trace_id=self.id)
        except Exception:  # noqa: BLE001
            return None


def flush() -> None:
    """Force-send buffered events. Called after eval runs and on app shutdown."""
    client = _client()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse flush failed: %s", exc)
