"""
Riskproof — end-to-end pipeline test on an in-memory EVM chain.

Tests:
1. Deploy RiskProof contract to local eth-tester provider.
2. Fund the client signer account.
3. High-risk action (medium+ severity) -> verifies on-chain commit.
4. Low-risk action -> verifies off-chain bypass without gas consumption.
5. Verify on-chain state inspection (eventCount and getRiskEvent).
"""

import json
from pathlib import Path
import pytest
from eth_account import Account
from eth_tester import EthereumTester
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from onchain_client import RiskProofClient
from risk_engine import Position, ProposedAction, ProposedChange


def load_artifact():
    custom_build = Path("build/RiskProof.json")
    default_artifact = Path("artifacts/contracts/RiskProof.sol/RiskProof.json")

    if custom_build.exists():
        with open(custom_build) as f:
            return json.load(f)
    elif default_artifact.exists():
        with open(default_artifact) as f:
            data = json.load(f)
            return {"abi": data["abi"], "bytecode": data["bytecode"]}
    else:
        raise FileNotFoundError(
            "Contract artifact not found. Run 'npx hardhat compile' before running pipeline tests."
        )


def create_test_context():
    """Initializes in-memory EVM, funds signer, deploys RiskProof, and returns client context."""
    artifact = load_artifact()
    abi = artifact["abi"]
    bytecode = artifact["bytecode"]

    eth_tester = EthereumTester()
    w3 = Web3(EthereumTesterProvider(eth_tester))
    faucet_account = w3.eth.accounts[0]

    # Deterministic test private key
    tester_private_key = (
        "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d"
    )
    client_address = Account.from_key(tester_private_key).address

    # Fund the client account with 10 ETH from the pre-funded genesis faucet
    w3.eth.send_transaction({
        "from": faucet_account,
        "to": client_address,
        "value": w3.to_wei(10, "ether"),
    })

    # Deploy contract
    factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = factory.constructor().transact({"from": faucet_account})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress

    client = RiskProofClient(
        w3=w3,
        contract_address=contract_address,
        abi=abi,
        private_key=tester_private_key,
    )

    return {
        "client": client,
        "contract_address": contract_address,
        "w3": w3,
    }


@pytest.fixture(scope="module")
def setup_chain():
    """Pytest fixture wrapper."""
    return create_test_context()


def test_high_risk_action_logged_onchain(setup_chain):
    """Actions with score >= 50 (medium/high/critical) must be logged on-chain."""
    client = setup_chain["client"]
    initial_count = client.event_count()

    risky_action = ProposedAction(
        agent_id="agent-pytest-001",
        action_type="increase_leverage",
        asset="ETH",
        current_position=Position(collateral=10000.0, debt=6000.0),
        proposed_change=ProposedChange(collateral_delta=0.0, debt_delta=2500.0),
    )

    result = client.check_and_log(risky_action)

    assert result["logged"] is True
    assert result["tx_hash"] is not None
    assert result["assessment"]["severity"] == "critical"
    assert result["assessment"]["risk_score"] == 100.0
    assert client.event_count() == initial_count + 1


def test_low_risk_action_bypasses_onchain(setup_chain):
    """Actions with score < 50 (low severity) must NOT consume gas or log on-chain."""
    client = setup_chain["client"]
    initial_count = client.event_count()

    safe_action = ProposedAction(
        agent_id="agent-pytest-002",
        action_type="add_collateral",
        asset="ETH",
        current_position=Position(collateral=10000.0, debt=3000.0),
        proposed_change=ProposedChange(collateral_delta=1000.0, debt_delta=0.0),
    )

    result = client.check_and_log(safe_action)

    assert result["logged"] is False
    assert result["tx_hash"] is None
    assert result["assessment"]["severity"] == "low"
    assert client.event_count() == initial_count


def test_onchain_event_retrieval(setup_chain):
    """Verify that getRiskEvent returns matching stored event data."""
    client = setup_chain["client"]
    count = client.event_count()
    assert count > 0, "Expected at least one logged event before retrieval"

    event_data = client.get_event(count - 1)
    assert event_data["agent_id"] == "agent-pytest-001"
    assert event_data["action_type"] == "increase_leverage"
    assert event_data["risk_score"] == 100


def main():
    """Manual runner for 'python3 test_pipeline.py' without pytest."""
    print("Running pipeline tests on local in-memory EVM chain...")
    ctx = create_test_context()

    test_high_risk_action_logged_onchain(ctx)
    print("✔ test_high_risk_action_logged_onchain passed")

    test_low_risk_action_bypasses_onchain(ctx)
    print("✔ test_low_risk_action_bypasses_onchain passed")

    test_onchain_event_retrieval(ctx)
    print("✔ test_onchain_event_retrieval passed")

    print("\nAll pipeline checks passed successfully!")


if __name__ == "__main__":
    main()