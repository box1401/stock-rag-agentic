from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types as gtypes

from app.core.logging import get_logger
from app.llm.types import ChatMessage, GenerationResult, ToolCall, ToolDefinition

log = get_logger(__name__)


class GeminiProvider:
    def __init__(self, api_key: str, primary: str, fallback: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self.primary_model = primary
        self.fallback_model = fallback

    async def call(
        self,
        model: str,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None,
        temperature: float,
        max_output_tokens: int,
    ) -> GenerationResult:
        system_text, contents = _to_genai_contents(messages)
        config = gtypes.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            system_instruction=system_text or None,
            tools=_to_genai_tools(tools) if tools else None,
        )
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return _parse_response(response, model)


def _to_genai_contents(messages: list[ChatMessage]) -> tuple[str, list[gtypes.Content]]:
    system_parts: list[str] = []
    contents: list[gtypes.Content] = []
    for m in messages:
        if m.role == "system":
            system_parts.append(m.content)
        elif m.role == "user":
            contents.append(gtypes.Content(role="user", parts=[gtypes.Part(text=m.content)]))
        elif m.role == "assistant":
            parts: list[gtypes.Part] = []
            if m.content:
                parts.append(gtypes.Part(text=m.content))
            for tc in m.tool_calls or []:
                parts.append(
                    gtypes.Part(function_call=gtypes.FunctionCall(name=tc.name, args=tc.arguments))
                )
            if not parts:
                parts.append(gtypes.Part(text=""))
            contents.append(gtypes.Content(role="model", parts=parts))
        elif m.role == "tool":
            contents.append(
                gtypes.Content(
                    role="user",
                    parts=[
                        gtypes.Part(
                            function_response=gtypes.FunctionResponse(
                                name=m.name or "tool",
                                response={"result": m.content},
                            )
                        )
                    ],
                )
            )
    return "\n\n".join(system_parts), contents


def _to_genai_tools(tools: list[ToolDefinition]) -> list[gtypes.Tool]:
    declarations = [
        gtypes.FunctionDeclaration(
            name=t.name,
            description=t.description,
            parameters=t.parameters or {"type": "object", "properties": {}},
        )
        for t in tools
    ]
    return [gtypes.Tool(function_declarations=declarations)]


def _parse_response(response: Any, model: str) -> GenerationResult:
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    finish: str = "stop"

    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        finish = _normalize_finish(getattr(cand, "finish_reason", None))
        content = getattr(cand, "content", None)
        if not content:
            continue
        for idx, part in enumerate(getattr(content, "parts", []) or []):
            if getattr(part, "text", None):
                text_parts.append(part.text)
            fc = getattr(part, "function_call", None)
            if fc and fc.name:
                args = dict(fc.args) if fc.args else {}
                tool_calls.append(
                    ToolCall(id=f"call_{idx}_{fc.name}", name=fc.name, arguments=args)
                )

    if tool_calls:
        finish = "tool_calls"

    usage = getattr(response, "usage_metadata", None)
    usage_dict = (
        {
            "prompt_tokens": getattr(usage, "prompt_token_count", 0) or 0,
            "completion_tokens": getattr(usage, "candidates_token_count", 0) or 0,
            "total_tokens": getattr(usage, "total_token_count", 0) or 0,
        }
        if usage
        else {}
    )

    return GenerationResult(
        text="".join(text_parts),
        tool_calls=tool_calls,
        finish_reason=finish,  # type: ignore[arg-type]
        model=model,
        usage=usage_dict,
    )


def _normalize_finish(raw: Any) -> str:
    if raw is None:
        return "stop"
    s = str(raw).lower()
    if "stop" in s:
        return "stop"
    if "max" in s or "length" in s:
        return "length"
    if "safety" in s:
        return "safety"
    return "other"
