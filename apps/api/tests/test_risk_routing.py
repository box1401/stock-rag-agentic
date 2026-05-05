from app.agents.risk_agent import MAX_REVISIONS, should_revise
from app.agents.state import RiskReview


def test_routing_pass_goes_to_reporter() -> None:
    state = {"risk": RiskReview(**{"pass": True}), "revisions": 0}
    assert should_revise(state) == "reporter"  # type: ignore[arg-type]


def test_routing_fail_first_time_revises() -> None:
    state = {"risk": RiskReview(**{"pass": False, "issues": ["x"]}), "revisions": 0}
    assert should_revise(state) == "revise"  # type: ignore[arg-type]


def test_routing_max_revisions_terminates() -> None:
    state = {
        "risk": RiskReview(**{"pass": False, "issues": ["x"]}),
        "revisions": MAX_REVISIONS,
    }
    assert should_revise(state) == "reporter"  # type: ignore[arg-type]


def test_routing_no_risk_goes_to_reporter() -> None:
    assert should_revise({"revisions": 0}) == "reporter"  # type: ignore[arg-type]
