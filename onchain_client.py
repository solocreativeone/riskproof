"""
Riskproof on-chain client.

Takes a proposed agent action, scores it with risk_engine.assess_action(),
and if severity is Medium or above, writes the assessment on-chain through
RiskProof.logRiskEvent(). Low severity actions are scored but not logged.

Config (environment variables, or a .env file):
    ARBITRUM_SEPOLIA_RPC_URL   RPC endpoint (default: public Arbitrum Sepolia RPC)
    DEPLOYER_PRIVATE_KEY       testnet wallet private key used to send the log tx
    RISKPROOF_CONTRACT_ADDRESS address of the deployed RiskProof contract
"""

import json
import os
from pathlib import Path
from typing import Optional

from web3 import Web3

from risk_engine import ProposedAction, RiskAssessment, assess_action

SEVERITY_TO_ENUM = {"low": 0, "medium": 1, "high": 2, "critical": 3}
LOG_THRESHOLD = {"medium", "high", "critical"}

DEFAULT_RPC = "https://sepolia-rollup.arbitrum.io/rpc"

# Hardhat writes the ABI here after `npx hardhat compile`.
HARDHAT_ARTIFACT = Path("artifacts/contracts/RiskProof.sol/RiskProof.json")


def load_abi(path: Optional[str] = None) -> list:
    artifact_path = Path(path) if path else HARDHAT_ARTIFACT
    with open(artifact_path) as f:
        return json.load(f)["abi"]


class RiskProofClient:
    def __init__(self, w3: Web3, contract_address: str, abi: list, private_key: str):
        self.w3 = w3
        self.account = w3.eth.account.from_key(private_key)
        self.contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )

    @classmethod
    def from_env(cls, abi_path: Optional[str] = None) -> "RiskProofClient":
        rpc = os.environ.get("ARBITRUM_SEPOLIA_RPC_URL", DEFAULT_RPC)
        key = os.environ["DEPLOYER_PRIVATE_KEY"]
        address = os.environ["RISKPROOF_CONTRACT_ADDRESS"]
        w3 = Web3(Web3.HTTPProvider(rpc))
        return cls(w3, address, load_abi(abi_path), key)

    def log_assessment(self, action: ProposedAction, assessment: RiskAssessment) -> str:
        """Send logRiskEvent() and return the transaction hash (hex)."""
        fn = self.contract.functions.logRiskEvent(
            action.agent_id,
            action.action_type,
            SEVERITY_TO_ENUM[assessment.severity],
            int(round(assessment.risk_score)),
            assessment.reason,
        )
        tx = fn.build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise RuntimeError(f"logRiskEvent transaction reverted: {tx_hash.hex()}")
        return tx_hash.hex()

    def check_and_log(self, action: ProposedAction) -> dict:
        """
        The full Riskproof pipeline for one proposed action:
        score it, then log on-chain if severity is Medium or above.
        """
        assessment = assess_action(action)
        result = {"assessment": assessment.to_dict(), "logged": False, "tx_hash": None}
        if assessment.severity in LOG_THRESHOLD:
            result["tx_hash"] = self.log_assessment(action, assessment)
            result["logged"] = True
        return result

    def event_count(self) -> int:
        return self.contract.functions.eventCount().call()

    def get_event(self, event_id: int) -> dict:
        e = self.contract.functions.getRiskEvent(event_id).call()
        return {
            "reporter": e[0],
            "agent_id": e[1],
            "action_type": e[2],
            "severity": e[3],
            "risk_score": e[4],
            "reason": e[5],
            "timestamp": e[6],
        }
