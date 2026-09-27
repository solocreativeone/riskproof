"""
Riskproof — risk scoring engine.

Takes a proposed agent action against a DeFi position and returns a risk
assessment: a 0-100 score, a severity tier (low/medium/high/critical), a
human-readable reason, and the projected health factor after the action.

This reuses the health-factor / liquidation-price logic from the
Health Factor Calculator project, applied to a *hypothetical* post-action
position instead of a live one, and reuses the Low/Medium/High/Critical
severity rubric from the Flare Summer Signal project.
"""

from dataclasses import dataclass, asdict
from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]


@dataclass
class Position:
    collateral: float
    debt: float


@dataclass
class ProposedChange:
    collateral_delta: float
    debt_delta: float


@dataclass
class ProposedAction:
    agent_id: str
    action_type: str
    asset: str
    current_position: Position
    proposed_change: ProposedChange


@dataclass
class RiskAssessment:
    risk_score: float
    severity: Severity
    reason: str
    projected_health_factor: float

    def to_dict(self) -> dict:
        return asdict(self)


# --- Health factor math -----------------------------------------------
#
# Simplified Aave-v3-style health factor:
#   health_factor = (collateral * liquidation_threshold) / debt
#
# A health factor below 1.0 means the position is liquidatable.
# liquidation_threshold is a placeholder default (see Health Factor
# Calculator's known limitation: not pulled live from any protocol).

DEFAULT_LIQUIDATION_THRESHOLD = 0.80


def compute_health_factor(collateral: float, debt: float,
                           liquidation_threshold: float = DEFAULT_LIQUIDATION_THRESHOLD) -> float:
    if debt <= 0:
        # No debt means no liquidation risk; return a large sentinel value.
        return float("inf")
    return (collateral * liquidation_threshold) / debt


# --- Severity mapping ----------------------------------------------------
#
# Maps a projected health factor to the Flare Summer Signal rubric.
# Thresholds are a starting point, tune them once you have real test
# scenarios to check them against.

def health_factor_to_severity(hf: float) -> Severity:
    if hf < 1.05:
        return "critical"
    if hf < 1.2:
        return "high"
    if hf < 1.5:
        return "medium"
    return "low"


def severity_to_score(severity: Severity, hf: float) -> float:
    """
    Maps severity + health factor into a 0-100 risk score for display
    and logging purposes. Lower health factor -> higher score within
    each tier.
    """
    if severity == "critical":
        return 100.0 if hf <= 1.0 else 90.0
    if severity == "high":
        return 75.0
    if severity == "medium":
        return 50.0
    return 15.0


# --- Main entry point ------------------------------------------------

def assess_action(action: ProposedAction) -> RiskAssessment:
    projected_collateral = action.current_position.collateral + action.proposed_change.collateral_delta
    projected_debt = action.current_position.debt + action.proposed_change.debt_delta

    projected_hf = compute_health_factor(projected_collateral, projected_debt)
    severity = health_factor_to_severity(projected_hf)
    score = severity_to_score(severity, projected_hf)

    reason = (
        f"Agent {action.agent_id} proposed '{action.action_type}' on {action.asset}: "
        f"collateral {action.current_position.collateral:.2f} -> {projected_collateral:.2f}, "
        f"debt {action.current_position.debt:.2f} -> {projected_debt:.2f}. "
        f"Projected health factor: {projected_hf:.3f} ({severity})."
    )

    return RiskAssessment(
        risk_score=score,
        severity=severity,
        reason=reason,
        projected_health_factor=projected_hf,
    )


if __name__ == "__main__":
    # Demo scenario: agent tries a risky leverage increase.
    demo_action = ProposedAction(
        agent_id="agent-001",
        action_type="increase_leverage",
        asset="ETH",
        current_position=Position(collateral=10000.0, debt=6000.0),
        proposed_change=ProposedChange(collateral_delta=0.0, debt_delta=2500.0),
    )

    result = assess_action(demo_action)
    print(result.to_dict())
