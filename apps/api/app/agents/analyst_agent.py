from __future__ import annotations

import json
import re
from typing import Any

from app.agents.state import AgentState, AgentTraceEvent, AnalystOutput
from app.core.logging import get_logger
from app.db import sessionmaker
from app.llm import ChatMessage, ToolCall, ToolDefinition, get_gateway
from app.rag.retrieval import hybrid_search
from app.tools.indicators import compute_indicators
from app.tools.news import jina_extract, tavily_search

log = get_logger(__name__)


_SYSTEM_ZH = (
    "你是一位嚴謹的台股研究員。你會收到目標個股的市場資料摘要，並且可以呼叫以下工具來補充資訊：\n"
    "  - rag_search(query, ticker?) — 從內部知識庫（thesis、年報、法說）檢索相關段落\n"
    "  - news_search(query) — 抓最近 14 天的新聞 headline + 摘要\n"
    "  - read_url(url) — 取得網頁全文（用於想深入特定新聞）\n\n"
    "策略：(1) 先呼叫 1-2 次 rag_search 找出該股的 thesis 與宏觀脈絡；"
    "(2) 視需要呼叫 news_search 確認近期催化或風險；"
    "(3) 整合資料後輸出最終 JSON。\n\n"
    "輸出格式（最終一次回應必須是純 JSON、不要 code fence）：\n"
    '{"headline": "...", "summary": "...", "bullets": ["...", "..."], '
    '"citations": [{"title": "...", "source_url": "..." (optional)}]}\n\n'
    "要求：summary 控制在 150-220 字；3-5 條 bullet；不可捏造資料中沒有的數字；語言：繁體中文。"
)

_SYSTEM_EN = (
    "You are a disciplined Taiwan-market equity researcher. You receive a market data summary "
    "for the target ticker and can call these tools:\n"
    "  - rag_search(query, ticker?) — search internal knowledge base (thesis, filings, transcripts)\n"
    "  - news_search(query) — fetch last 14 days of news headlines + snippets\n"
    "  - read_url(url) — get full text of a webpage (when you need to dig deeper)\n\n"
    "Strategy: (1) call rag_search 1-2 times to retrieve the thesis and macro context; "
    "(2) optionally call news_search to confirm recent catalysts; "
    "(3) integrate everything and emit the final JSON.\n\n"
    "Final response must be pure JSON, no code fence:\n"
    '{"headline": "...", "summary": "...", "bullets": ["...", "..."], '
    '"citations": [{"title": "...", "source_url": "..." (optional)}]}\n\n'
    "Constraints: summary 100-180 words; 3-5 bullets; never fabricate numbers absent from data; "
    "language: English."
)


def _tool_defs() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name="rag_search",
            description="Search the internal knowledge base (thesis notes, filings, transcripts).",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, in any language."},
                    "ticker": {"type": "string", "description": "Optional ticker filter, e.g. '2330'."},
                    "top_k": {"type": "integer", "description": "How many top results to return (1-8).", "default": 5},
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="news_search",
            description="Search the open web for news from the last 14 days.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query, in Chinese or English."},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        ToolDefinition(
            name="read_url",
            description="Fetch the full clean article text for a single URL.",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        ),
    ]


def _initial_user(state: AgentState, indicators_dict: dict[str, Any] | None) -> str:
    data = state["data"]
    payload = {
        "ticker": state["ticker"],
        "mode": state.get("mode", "on_demand"),
        "indicators": indicators_dict,
        "fundamentals": data.fundamentals.model_dump() if data.fundamentals else None,
        "recent_prices": [p.model_dump() for p in (data.prices or [])[-5:]],
        "institutional_5d": [r.model_dump() for r in (data.institutional or [])[:5]],
        "margin_5d": [r.model_dump() for r in (data.margin or [])[:5]],
        "revenue_recent_months": [r.model_dump() for r in (data.revenue or [])[:6]],
    }
    return (
        "Target ticker: "
        + state["ticker"]
        + "\n\nMarket data summary (already fetched):\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
        + "\n\nNow plan your tool calls and produce the final research note."
    )


def _extract_json(text: str) -> dict[str, Any]:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json object in model output")
    return json.loads(candidate[start : end + 1])


async def _exec_tool(call: ToolCall, ticker_hint: str | None) -> tuple[str, list[dict[str, Any]]]:
    """Execute one tool call. Returns (text result, citation rows)."""
    name = call.name
    args = call.arguments or {}

    if name == "rag_search":
        async with sessionmaker() as session:
            results = await hybrid_search(
                session,
                query=str(args.get("query", "")),
                ticker=str(args["ticker"]) if args.get("ticker") else ticker_hint,
                top_k=int(args.get("top_k", 5) or 5),
            )
        if not results:
            return "(no results)", []
        lines = []
        cites = []
        for i, r in enumerate(results, 1):
            lines.append(
                f"[{i}] {r.title or r.source_type or 'doc'}\n{r.content[:600].strip()}"
            )
            cites.append(
                {
                    "title": r.title,
                    "source_url": r.source_url,
                    "source_type": r.source_type,
                    "ticker": r.ticker,
                    "chunk_id": str(r.chunk_id),
                    "score": round(r.score, 4),
                }
            )
        return "\n\n".join(lines), cites

    if name == "news_search":
        hits = await tavily_search(str(args.get("query", "")), max_results=int(args.get("max_results", 5) or 5))
        if not hits:
            return "(news_search returned 0 results — no API key or quiet news)", []
        lines = [f"[{i+1}] {h.title} ({h.source})\n{h.snippet}\nURL: {h.url}" for i, h in enumerate(hits)]
        cites = [{"title": h.title, "source_url": h.url, "source_type": "news"} for h in hits]
        return "\n\n".join(lines), cites

    if name == "read_url":
        url = str(args.get("url", ""))
        text = await jina_extract(url)
        if not text:
            return f"(read_url failed for {url})", []
        return text[:4000], [{"title": "web", "source_url": url, "source_type": "web"}]

    return f"(unknown tool: {name})", []


async def analyst_node(state: AgentState) -> AgentState:
    trace: list[AgentTraceEvent] = list(state.get("trace") or [])
    data = state.get("data")
    if not data:
        trace.append(AgentTraceEvent(agent="analyst", event="skipped", detail={"reason": "no_data"}))
        return {**state, "trace": trace}

    indicators = compute_indicators(data.prices)
    indicators_dict = indicators.model_dump() if indicators else None

    trace.append(
        AgentTraceEvent(
            agent="analyst",
            event="indicators_computed",
            detail=indicators_dict or {"warning": "insufficient_history"},
        )
    )

    language = state.get("language", "zh-TW")
    system = _SYSTEM_ZH if language == "zh-TW" else _SYSTEM_EN
    ticker = state["ticker"]
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=_initial_user(state, indicators_dict)),
    ]

    gateway = get_gateway()
    tools = _tool_defs()
    citations: list[dict[str, Any]] = []
    parsed: dict[str, Any] | None = None
    last_text = ""
    last_model = ""

    MAX_ITER = 5
    for step in range(MAX_ITER):
        result = await gateway.generate(messages=messages, tools=tools, temperature=0.2, max_output_tokens=4096)
        last_text = result.text
        last_model = result.model

        if not result.tool_calls:
            try:
                parsed = _extract_json(result.text)
            except Exception as e:  # noqa: BLE001
                log.warning("analyst_parse_failed err=%s preview=%r", e, result.text[:200])
            break

        messages.append(ChatMessage(role="assistant", content=result.text or "", tool_calls=result.tool_calls))
        for tc in result.tool_calls:
            tool_text, tool_cites = await _exec_tool(tc, ticker)
            citations.extend(tool_cites)
            trace.append(
                AgentTraceEvent(
                    agent="analyst",
                    event=f"tool:{tc.name}",
                    detail={"args": tc.arguments, "result_chars": len(tool_text)},
                )
            )
            messages.append(
                ChatMessage(role="tool", name=tc.name, content=tool_text, tool_call_id=tc.id)
            )

    if parsed is None:
        parsed = {
            "headline": f"{ticker} — preliminary read",
            "summary": (last_text or "Analysis output unavailable.").strip()[:600],
            "bullets": [],
            "citations": [],
        }

    output = AnalystOutput(
        headline=str(parsed.get("headline", ""))[:200],
        summary=str(parsed.get("summary", "")),
        bullets=[str(b) for b in (parsed.get("bullets") or [])][:8],
        indicators=indicators,
        citations=citations + list(parsed.get("citations") or []),
    )

    trace.append(
        AgentTraceEvent(
            agent="analyst",
            event="draft_done",
            detail={
                "bullets": len(output.bullets),
                "tool_calls": sum(1 for t in trace if t.agent == "analyst" and t.event.startswith("tool:")),
                "model": last_model,
            },
        )
    )

    return {**state, "analyst": output, "trace": trace}
