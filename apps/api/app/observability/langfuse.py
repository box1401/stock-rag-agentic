"""Langfuse instrumentation. Degrades to a no-op when keys are absent.

Use as decorators / context managers around the three layers we care about:

  - `trace_pipeline(ticker, mode, language)` — wraps an entire /analyze run
  - `trace_agent(name)` — wraps a LangGraph node
  - `trace_llm_call(model)` — wraps a single LLM gateway call

Each layer creates a span / generation under a single trace_id so the
Langfuse UI shows the agent flow as a tree.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from functools import lru_cache, wraps
from typing import Any, ParamSpec, TypeVar

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

_current_trace: ContextVar[Any | None] = ContextVar("_current_trace", default=None)
P = ParamSpec("P")
R = TypeVar("R")


@lru_cache
def get_langfuse() -> Any | None:
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return None
    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]
    except Exception as e:
        log.warning("langfuse_import_failed err=%s", e)
        return None
    try:
        return Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
    except Exception as e:
        log.warning("langfuse_init_failed err=%s", e)
        return None


def is_enabled() -> bool:
    return get_langfuse() is not None


@asynccontextmanager
async def trace_pipeline(ticker: str, mode: str, language: str) -> AsyncIterator[Any | None]:
    """Top-level trace covering one /analyze invocation."""
    lf = get_langfuse()
    if lf is None:
        yield None
        return
    try:
        trace = lf.trace(
            name="analyze",
            input={"ticker": ticker, "mode": mode, "language": language},
            tags=[f"ticker:{ticker}", f"lang:{language}", f"mode:{mode}"],
        )
    except Exception as e:
        log.warning("langfuse_trace_create_failed err=%s", e)
        yield None
        return

    token = _current_trace.set(trace)
    try:
        yield trace
    finally:
        _current_trace.reset(token)
        try:
            lf.flush()
        except Exception:
            pass


def trace_agent(name: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Wrap a LangGraph async node so each invocation becomes a span."""

    def deco(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(fn)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            trace = _current_trace.get()
            if trace is None:
                return await fn(*args, **kwargs)
            span = None
            try:
                span = trace.span(name=f"agent:{name}")
            except Exception:
                return await fn(*args, **kwargs)
            try:
                result = await fn(*args, **kwargs)
                if span is not None:
                    try:
                        span.end()
                    except Exception:
                        pass
                return result
            except Exception as exc:
                if span is not None:
                    try:
                        span.end(level="ERROR", status_message=str(exc))
                    except Exception:
                        pass
                raise

        return inner

    return deco


@asynccontextmanager
async def trace_llm_call(
    model: str, prompt_summary: str, *, name: str = "gemini"
) -> AsyncIterator[Callable[[str, dict[str, int]], None]]:
    """Span for one LLM call. Caller invokes the yielded callback with (output_text, usage)."""
    trace = _current_trace.get()
    gen = None
    if trace is not None:
        try:
            gen = trace.generation(
                name=name,
                model=model,
                input=prompt_summary[:2000],
            )
        except Exception:
            gen = None

    def finish(output: str, usage: dict[str, int]) -> None:
        if gen is None:
            return
        try:
            gen.end(
                output=output[:4000],
                usage={
                    "input": usage.get("prompt_tokens", 0),
                    "output": usage.get("completion_tokens", 0),
                    "total": usage.get("total_tokens", 0),
                },
            )
        except Exception:
            pass

    try:
        yield finish
    except Exception as exc:
        if gen is not None:
            try:
                gen.end(level="ERROR", status_message=str(exc))
            except Exception:
                pass
        raise
