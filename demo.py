"""
Riskproof live demo: run two proposed agent actions through the full pipeline
against the deployed contract on Arbitrum Sepolia.

Needs a .env file with:
    DEPLOYER_PRIVATE_KEY=<testnet wallet key, funded with Sepolia ETH>
    RISKPROOF_CONTRACT_ADDRESS=<address printed by scripts/deploy.js>
    ARBITRUM_SEPOLIA_RPC_URL=<optional, defaults to the public RPC>
    TELEGRAM_BOT_TOKEN=<optional, for Telegram alert dispatch>
    TELEGRAM_CHAT_ID=<optional, for Telegram alert dispatch>
"""

from dotenv import load_dotenv

from notifier import send_telegram_alert
from onchain_client import RiskProofClient
from risk_engine import Position, ProposedAction, ProposedChange

EXPLORER_TX = "https://sepolia.arbiscan.io/tx/0x"


def build_action(action_type, collateral, debt, collateral_delta, debt_delta):
    return ProposedAction(
        agent_id="agent-001",
        action_type=action_type,
        asset="ETH",
        current_position=Position(collateral=collateral, debt=debt),
        proposed_change=ProposedChange(collateral_delta=collateral_delta, debt_delta=debt_delta),
    )


def show(label, result):
    a = result["assessment"]
    print(f"\n=== {label} ===")
    print(f"severity: {a['severity'].upper()}  score: {a['risk_score']}  projected HF: {a['projected_health_factor']:.3f}")
    print(f"reason:   {a['reason']}")
    if result["logged"]:
        tx = result["tx_hash"].removeprefix("0x")
        print(f"LOGGED ON-CHAIN: {EXPLORER_TX}{tx}")

        # Dispatch Telegram notification for on-chain logged events
        send_telegram_alert(
            agent_id="agent-001",
            severity=a["severity"],
            risk_score=a["risk_score"],
            projected_hf=a["projected_health_factor"],
            reason=a["reason"],
            tx_hash=result["tx_hash"],
        )
    else:
        print("not logged (below Medium severity)")


def main():
    load_dotenv()
    client = RiskProofClient.from_env()

    print("Scenario 1: agent tries a risky leverage increase")
    show("Risky action", client.check_and_log(build_action("increase_leverage", 10000, 6000, 0, 2500)))

    print("\nScenario 2: agent adds collateral (safe)")
    show("Safe action", client.check_and_log(build_action("add_collateral", 10000, 3000, 1000, 0)))

    print(f"\nTotal events on-chain: {client.event_count()}")


if __name__ == "__main__":
    main()