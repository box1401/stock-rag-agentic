from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.llm.providers.base import LLMProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.types import ChatMessage, GenerationResult, ToolDefinition

log = get_logger(__name__)


class LLMError(RuntimeError):
    pass


class LLMGateway:
    """Single entry-point for all LLM calls. Falls back primary -> fallback model on hard error."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    @property
    def primary(self) -> str:
        return self._provider.primary_model

    @property
    def fallback(self) -> str:
        return self._provider.fallback_model

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        force_model: str | None = None,
    ) -> GenerationResult:
        from app.observability import trace_llm_call

        models_to_try = [force_model] if force_model else [self.primary, self.fallback]
        last_err: Exception | None = None
        prompt_summary = "\n".join(f"[{m.role}] {(m.content or '')[:300]}" for m in messages[-3:])

        for model in models_to_try:
            assert model is not None
            try:
                async with trace_llm_call(model, prompt_summary) as finish:
                    result = await self._call(
                        model, messages, tools, temperature, max_output_tokens
                    )
                    finish(result.text, result.usage)
                    return result
            except Exception as e:
                last_err = e
                log.warning("llm_call_failed", model=model, error=str(e))
        raise LLMError(f"All LLM models failed; last={last_err}") from last_err

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None,
        temperature: float,
        max_output_tokens: int,
    ) -> GenerationResult:
        return await self._provider.call(model, messages, tools, temperature, max_output_tokens)


def tool_args_as_json(args: dict[str, Any]) -> str:
    return json.dumps(args, ensure_ascii=False)


@lru_cache
def get_gateway() -> LLMGateway:
    s = get_settings()
    provider: LLMProvider
    if s.llm_provider == "ollama":
        log.info(
            "llm_provider=ollama",
            base_url=s.ollama_base_url,
            primary=s.ollama_model_primary,
            fallback=s.ollama_model_fallback,
        )
        provider = OllamaProvider(
            base_url=s.ollama_base_url,
            primary=s.ollama_model_primary,
            fallback=s.ollama_model_fallback,
        )
    else:
        if not s.gemini_api_key:
            log.warning("gemini_api_key_missing — gateway will fail on call")
        provider = GeminiProvider(
            api_key=s.gemini_api_key,
            primary=s.gemini_model_primary,
            fallback=s.gemini_model_fallback,
        )
    return LLMGateway(provider)
