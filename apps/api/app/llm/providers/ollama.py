"""Ollama provider via OpenAI-compatible /v1/chat/completions endpoint.

Function calling: Ollama 0.4+ supports tools natively; Qwen2.5 / Llama 3.1+ /
Mistral 0.3+ / hermes-3 emit tool_calls correctly. Older models silently ignore
the `tools` array, which the agent loop tolerates (no tool_calls -> finalise).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from app.core.logging import get_logger
from app.llm.types import ChatMessage, GenerationResult, ToolCall, ToolDefinition

log = get_logger(__name__)


class OllamaProvider:
    def __init__(self, base_url: str, primary: str, fallback: str) -> None:
        self._base_url = base_url.rstrip("/")
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
        body: dict[str, Any] = {
            "model": model,
            "messages": _to_openai_messages(messages),
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "stream": False,
        }
        if tools:
            body["tools"] = _to_openai_tools(tools)
            body["tool_choice"] = "auto"

        url = f"{self._base_url}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        return _parse_openai_response(data, model)


def _to_openai_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            out.append({"role": "system", "content": m.content})
        elif m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id or f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in m.tool_calls
                ]
            out.append(entry)
        elif m.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "name": m.name or "tool",
                    "content": m.content,
                    "tool_call_id": m.tool_call_id or f"call_{uuid.uuid4().hex[:8]}",
                }
            )
    return out


def _to_openai_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters or {"type": "object", "properties": {}},
            },
        }
        for t in tools
    ]


def _parse_openai_response(data: dict[str, Any], model: str) -> GenerationResult:
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    text = str(msg.get("content") or "")

    tool_calls: list[ToolCall] = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        raw_args = fn.get("arguments")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
        except json.JSONDecodeError:
            log.warning("ollama_tool_args_unparseable raw=%r", raw_args)
            args = {}
        tool_calls.append(
            ToolCall(
                id=str(tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"),
                name=str(fn.get("name") or ""),
                arguments=args,
            )
        )

    finish_raw = str(choice.get("finish_reason") or "stop").lower()
    if tool_calls:
        finish = "tool_calls"
    elif finish_raw in ("length", "max_tokens"):
        finish = "length"
    elif "safety" in finish_raw or finish_raw == "content_filter":
        finish = "safety"
    elif finish_raw == "stop":
        finish = "stop"
    else:
        finish = "other"

    usage = data.get("usage") or {}
    return GenerationResult(
        text=text,
        tool_calls=tool_calls,
        finish_reason=finish,  # type: ignore[arg-type]
        model=str(data.get("model") or model),
        usage={
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        },
    )
