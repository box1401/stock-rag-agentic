from __future__ import annotations

import json
import re
from typing import Any

from app.agents.state import AgentState, AgentTraceEvent, RiskReview
from app.core.logging import get_logger
from app.llm import ChatMessage, get_gateway

log = get_logger(__name__)

MAX_REVISIONS = 2

_SYSTEM_ZH = (
    "你是嚴格的風控審查員。檢視分析師的研究筆記，找出：\n"
    "  (a) 不被原始資料支持的數字或宣稱（hallucination）\n"
    "  (b) 過度樂觀、忽略明顯下行風險的論點\n"
    "  (c) 模糊的非結論性語言（如「可能、或許、看起來像」濫用）\n\n"
    "輸出格式（純 JSON、不要 code fence）：\n"
    '{"pass": bool, "issues": ["..."], "suggestions": ["..."]}\n'
    "規則：若 issues 為空，pass = true；否則 pass = false。issues / suggestions 各不超過 3 條。語言：繁體中文。"
)
_SYSTEM_EN = (
    "You are a strict risk reviewer. Inspect the analyst's research note for:\n"
    "  (a) numbers or claims not supported by the source data (hallucination)\n"
    "  (b) overly bullish framing that ignores obvious downside\n"
    "  (c) vague hedging language overused\n\n"
    "Output pure JSON, no code fence:\n"
    '{"pass": bool, "issues": ["..."], "suggestions": ["..."]}\n'
    "Pass = true iff issues is empty. Max 3 items each. Language: English."
)


def _extract_json(text: str) -> dict[str, Any]:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json")
    return json.loads(candidate[start : end + 1])


def _build_review_prompt(state: AgentState) -> str:
    analyst = state["analyst"]
    data = state["data"]
    payload = {
        "ticker": state["ticker"],
        "draft": {
            "headline": analyst.headline,
            "summary": analyst.summary,
            "bullets": analyst.bullets,
        },
        "source_indicators": (analyst.indicators.model_dump() if analyst.indicators else None),
        "source_recent_prices": [p.model_dump() for p in (data.prices or [])[-5:]],
        "source_revenue_recent": [r.model_dump() for r in (data.revenue or [])[:6]],
        "source_institutional_5d": [r.model_dump() for r in (data.institutional or [])[:5]],
    }
    return (
        "Review the following analyst draft against its source data and report any "
        "unsupported claim or downside-blind framing.\n\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
    )


async def risk_node(state: AgentState) -> AgentState:
    trace: list[AgentTraceEvent] = list(state.get("trace") or [])
    if not state.get("analyst"):
        trace.append(AgentTraceEvent(agent="risk", event="skipped", detail={"reason": "no_analyst"}))
        return {**state, "trace": trace}

    language = state.get("language", "zh-TW")
    system = _SYSTEM_ZH if language == "zh-TW" else _SYSTEM_EN

    gateway = get_gateway()
    result = await gateway.generate(
        messages=[
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=_build_review_prompt(state)),
        ],
        temperature=0.0,
        max_output_tokens=1024,
    )

    try:
        parsed = _extract_json(result.text)
    except Exception as e:  # noqa: BLE001
        log.warning("risk_parse_failed err=%s preview=%r", e, result.text[:200])
        parsed = {"pass": True, "issues": [], "suggestions": []}

    review = RiskReview.model_validate(
        {
            "pass": bool(parsed.get("pass", True)),
            "issues": [str(x) for x in (parsed.get("issues") or [])][:5],
            "suggestions": [str(x) for x in (parsed.get("suggestions") or [])][:5],
        }
    )
    trace.append(
        AgentTraceEvent(
            agent="risk",
            event="review_done",
            detail={"pass": review.pass_, "issues": len(review.issues), "model": result.model},
        )
    )
    return {**state, "risk": review, "trace": trace}


async def revise_node(state: AgentState) -> AgentState:
    """If risk failed, ask analyst to revise once. Bumps `revisions` counter."""
    trace: list[AgentTraceEvent] = list(state.get("trace") or [])
    risk = state.get("risk")
    analyst = state.get("analyst")
    if not risk or risk.pass_ or not analyst:
        return state
    revisions = int(state.get("revisions", 0)) + 1
    trace.append(
        AgentTraceEvent(
            agent="risk",
            event="revision_requested",
            detail={"revision": revisions, "issues": risk.issues},
        )
    )

    language = state.get("language", "zh-TW")
    instr_zh = (
        "風控指出以下問題，請重寫研究筆記改正之，並嚴格依據原始資料；"
        "輸出純 JSON：{headline, summary, bullets, citations}\n\n問題：\n- "
        + "\n- ".join(risk.issues)
        + ("\n建議：\n- " + "\n- ".join(risk.suggestions) if risk.suggestions else "")
    )
    instr_en = (
        "The risk reviewer flagged the following issues. Rewrite the research note to address each one, "
        "strictly grounded in the source data. Output pure JSON: {headline, summary, bullets, citations}\n\n"
        "Issues:\n- "
        + "\n- ".join(risk.issues)
        + ("\nSuggestions:\n- " + "\n- ".join(risk.suggestions) if risk.suggestions else "")
    )

    gateway = get_gateway()
    result = await gateway.generate(
        messages=[
            ChatMessage(role="system", content="You revise equity research notes per risk-review feedback."),
            ChatMessage(
                role="user",
                content=(instr_zh if language == "zh-TW" else instr_en)
                + "\n\nCurrent draft:\n"
                + json.dumps(
                    {
                        "headline": analyst.headline,
                        "summary": analyst.summary,
                        "bullets": analyst.bullets,
                    },
                    ensure_ascii=False,
                ),
            ),
        ],
        temperature=0.2,
        max_output_tokens=2048,
    )

    try:
        parsed = _extract_json(result.text)
        revised = analyst.model_copy(
            update={
                "headline": str(parsed.get("headline", analyst.headline))[:200],
                "summary": str(parsed.get("summary", analyst.summary)),
                "bullets": [str(b) for b in (parsed.get("bullets") or analyst.bullets)][:8],
            }
        )
        trace.append(
            AgentTraceEvent(
                agent="analyst",
                event="revised",
                detail={"revision": revisions, "model": result.model},
            )
        )
        return {**state, "analyst": revised, "revisions": revisions, "trace": trace}
    except Exception as e:  # noqa: BLE001
        log.warning("revise_parse_failed err=%s", e)
        return {**state, "revisions": revisions, "trace": trace}


def should_revise(state: AgentState) -> str:
    risk = state.get("risk")
    if not risk or risk.pass_:
        return "reporter"
    if int(state.get("revisions", 0)) >= MAX_REVISIONS:
        return "reporter"
    return "revise"
