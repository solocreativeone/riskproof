"""
Riskproof FastMCP Server.

Exposes tools for autonomous AI agents to simulate DeFi risk and commit
verifiable accountability proofs directly to Arbitrum Sepolia before execution.
"""

from typing import Any, Dict, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP

from notifier import send_telegram_alert
from onchain_client import RiskProofClient
from risk_engine import Position, ProposedAction, ProposedChange, assess_action

load_dotenv()

mcp = FastMCP("RiskProof Engine")

_client: Optional[RiskProofClient] = None


def get_client() -> RiskProofClient:
    global _client
    if _client is None:
        _client = RiskProofClient.from_env()
    return _client


@mcp.tool()
def simulate_risk(
    agent_id: str,
    action_type: str,
    asset: str,
    current_collateral: float,
    current_debt: float,
    collateral_delta: float = 0.0,
    debt_delta: float = 0.0,
) -> Dict[str, Any]:
    """Simulates DeFi action risk without spending gas or sending a transaction.

    Calculates projected health factor, severity tier (low/medium/high/critical),
    risk score (0-100), and explanation reason.
    """
    action = ProposedAction(
        agent_id=agent_id,
        action_type=action_type,
        asset=asset,
        current_position=Position(collateral=current_collateral, debt=current_debt),
        proposed_change=ProposedChange(
            collateral_delta=collateral_delta, debt_delta=debt_delta
        ),
    )
    assessment = assess_action(action)
    return {
        "agent_id": agent_id,
        "action_type": action_type,
        "asset": asset,
        "severity": assessment.severity,
        "risk_score": assessment.risk_score,
        "projected_health_factor": round(assessment.projected_health_factor, 3),
        "reason": assessment.reason,
        "requires_onchain_proof": assessment.severity in ("medium", "high", "critical"),
    }


@mcp.tool()
def evaluate_and_log_action(
    agent_id: str,
    action_type: str,
    asset: str,
    current_collateral: float,
    current_debt: float,
    collateral_delta: float = 0.0,
    debt_delta: float = 0.0,
) -> Dict[str, Any]:
    """Evaluates the risk of a proposed action and records proof on Arbitrum Sepolia

    if the severity meets or exceeds the MEDIUM threshold. Dispatches a Telegram
    alert if logged on-chain.
    """
    client = get_client()
    action = ProposedAction(
        agent_id=agent_id,
        action_type=action_type,
        asset=asset,
        current_position=Position(collateral=current_collateral, debt=current_debt),
        proposed_change=ProposedChange(
            collateral_delta=collateral_delta, debt_delta=debt_delta
        ),
    )
    result = client.check_and_log(action)
    assessment = result["assessment"]

    tx_hash = result.get("tx_hash")
    arbiscan_url = (
        f"https://sepolia.arbiscan.io/tx/{tx_hash}" if tx_hash else None
    )

    # Dispatch Telegram alert on successful on-chain commit
    if result.get("logged"):
        send_telegram_alert(
            agent_id=agent_id,
            severity=assessment["severity"],
            risk_score=assessment["risk_score"],
            projected_hf=assessment["projected_health_factor"],
            reason=assessment["reason"],
            tx_hash=tx_hash,
        )

    return {
        "agent_id": agent_id,
        "severity": assessment["severity"],
        "risk_score": assessment["risk_score"],
        "projected_health_factor": round(assessment["projected_health_factor"], 3),
        "reason": assessment["reason"],
        "logged_on_chain": result["logged"],
        "tx_hash": tx_hash,
        "arbiscan_url": arbiscan_url,
    }


@mcp.tool()
def get_onchain_event_count() -> int:
    """Returns the total number of accountability risk events logged on-chain."""
    client = get_client()
    return client.event_count()


if __name__ == "__main__":
    mcp.run()