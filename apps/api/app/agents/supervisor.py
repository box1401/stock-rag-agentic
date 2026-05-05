from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.analyst_agent import analyst_node
from app.agents.data_agent import data_node
from app.agents.reporter_agent import reporter_node
from app.agents.risk_agent import revise_node, risk_node, should_revise
from app.agents.state import AgentState, AgentTraceEvent
from app.core.logging import get_logger
from app.observability import trace_agent, trace_pipeline

log = get_logger(__name__)


async def supervisor_node(state: AgentState) -> AgentState:
    trace = list(state.get("trace") or [])
    trace.append(
        AgentTraceEvent(
            agent="supervisor",
            event="dispatch",
            detail={"ticker": state.get("ticker"), "mode": state.get("mode", "on_demand")},
        )
    )
    return {**state, "trace": trace, "revisions": state.get("revisions", 0)}


def build_graph() -> Any:
    graph: StateGraph[AgentState] = StateGraph(AgentState)
    graph.add_node("supervisor", trace_agent("supervisor")(supervisor_node))
    graph.add_node("data", trace_agent("data")(data_node))
    graph.add_node("analyst", trace_agent("analyst")(analyst_node))
    graph.add_node("risk", trace_agent("risk")(risk_node))
    graph.add_node("revise", trace_agent("revise")(revise_node))
    graph.add_node("reporter", trace_agent("reporter")(reporter_node))

    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "data")
    graph.add_edge("data", "analyst")
    graph.add_edge("analyst", "risk")
    graph.add_conditional_edges("risk", should_revise, {"revise": "revise", "reporter": "reporter"})
    graph.add_edge("revise", "risk")
    graph.add_edge("reporter", END)
    return graph.compile()


_compiled: Any = None


def _get_compiled() -> Any:
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


async def run_pipeline(
    ticker: str,
    mode: str = "on_demand",
    language: str = "zh-TW",
) -> AgentState:
    initial: AgentState = {
        "ticker": ticker,
        "mode": mode,  # type: ignore[typeddict-item]
        "language": language,  # type: ignore[typeddict-item]
        "trace": [],
        "revisions": 0,
    }
    async with trace_pipeline(ticker, mode, language):
        result = await _get_compiled().ainvoke(initial)
    return result  # type: ignore[no-any-return]
