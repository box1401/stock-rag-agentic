from __future__ import annotations

from typing import Protocol

from app.llm.types import ChatMessage, GenerationResult, ToolDefinition


class LLMProvider(Protocol):
    """Common surface every LLM backend must implement."""

    primary_model: str
    fallback_model: str

    async def call(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None,
        temperature: float,
        max_output_tokens: int,
    ) -> GenerationResult: ...
