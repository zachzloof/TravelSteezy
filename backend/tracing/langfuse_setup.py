"""Langfuse tracing.

One top-level trace per user turn, one span per agent and per tool call, so the
orchestrator fan-out and the final synthesis show up as a tree in the Langfuse UI.

When Langfuse keys are absent every object here becomes a no-op with the same
interface, so tracing can never take down a chat turn and the app runs fine
without the service. Trace ids are generated locally either way, which is what
lets an eval run be tagged and correlated even in offline mode.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
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


def tracing_enabled() -> bool:
    return _client() is not None


class _NoOpSpan:
    """Same surface as a Langfuse span, does nothing."""

    def end(self, **_: Any) -> None:
        return None

    def update(self, **_: Any) -> None:
        return None

    def span(self, **_: Any) -> "_NoOpSpan":
        return self

    def generation(self, **_: Any) -> "_NoOpSpan":
        return self


class Trace:
    """A single user turn. Wraps a Langfuse trace, or nothing at all."""

    def __init__(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        input: Any = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        # Recorded locally regardless of Langfuse, so /chat can always return a
        # per-agent timing breakdown for the demo panel.
        self.spans: list[dict[str, Any]] = []
        self._handle: Any = None

        client = _client()
        if client is not None:
            try:
                self._handle = client.trace(
                    id=self.id,
                    name=name,
                    user_id=user_id,
                    session_id=session_id,
                    metadata=metadata,
                    tags=tags,
                    input=input,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse trace creation failed: %s", exc)
                self._handle = None

    @contextmanager
    def span(
        self, name: str, input: Any = None, metadata: dict[str, Any] | None = None
    ) -> Iterator[Any]:
        """Time a child operation (an agent, a tool call, a retrieval)."""
        started = time.perf_counter()
        handle: Any = _NoOpSpan()
        if self._handle is not None:
            try:
                handle = self._handle.span(name=name, input=input, metadata=metadata)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse span creation failed: %s", exc)

        record: dict[str, Any] = {"name": name, "status": "ok", "summary": None}
        try:
            yield handle
        except Exception as exc:
            record["status"] = "error"
            record["summary"] = f"{type(exc).__name__}: {exc}"
            try:
                handle.end(level="ERROR", status_message=str(exc))
            except Exception:  # noqa: BLE001
                pass
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.spans.append(record)
            raise
        else:
            record["duration_ms"] = int((time.perf_counter() - started) * 1000)
            self.spans.append(record)
            try:
                handle.end()
            except Exception:  # noqa: BLE001
                pass

    def note(self, name: str, summary: str, status: str = "ok", duration_ms: int | None = None) -> None:
        """Record a span that was not timed inline (e.g. a skipped agent)."""
        self.spans.append(
            {"name": name, "status": status, "summary": summary, "duration_ms": duration_ms}
        )

    def set_span_summary(self, name: str, summary: str) -> None:
        for record in reversed(self.spans):
            if record["name"] == name:
                record["summary"] = summary
                return

    def end(self, output: Any = None, metadata: dict[str, Any] | None = None) -> None:
        if self._handle is not None:
            try:
                self._handle.update(output=output, metadata=metadata)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Langfuse trace update failed: %s", exc)

    @property
    def url(self) -> str | None:
        if not settings.langfuse_enabled:
            return None
        return f"{settings.langfuse_host.rstrip('/')}/trace/{self.id}"


def flush() -> None:
    """Force-send buffered events. Called after eval runs and on app shutdown."""
    client = _client()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Langfuse flush failed: %s", exc)
