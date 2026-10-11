# Riskproof

Verifiable on-chain accountability layer for AI agents acting in DeFi. Built for Colosseum's Crypto World's Fair.

Autonomous AI agents executing DeFi transactions face severe principal-agent risks: reckless leverage, catastrophic liquidations, and hallucinated position sizing. Riskproof provides a pre-flight risk evaluation engine and a permanent on-chain accountability trail on Arbitrum Sepolia.

Instead of paying gas on routine actions, Riskproof logs on-chain only when severity is Medium or higher. Low-risk actions are scored off-chain at no gas cost. Medium, High, and Critical assessments are written to the RiskProof contract on Arbitrum Sepolia as a public, timestamped record, and the position owner gets a real-time Telegram alert.

---

## Verified Deployment

- Network: Arbitrum Sepolia (Chain ID: 421614)
- Contract Address: `0xA0046934fd8627695Ba76A879E421083C2487564`
- Verified Contract Code: [https://sepolia.arbiscan.io/address/0xA0046934fd8627695Ba76A879E421083C2487564#code](https://sepolia.arbiscan.io/address/0xA0046934fd8627695Ba76A879E421083C2487564#code)
- Sample Logged Transaction: [`0xa9d1fad970c67e123f46050db4d370b073edc707a983141482e69035e200e046`](https://sepolia.arbiscan.io/tx/0xa9d1fad970c67e123f46050db4d370b073edc707a983141482e69035e200e046)

---

## Architecture Flow

Riskproof decouples fast pre-flight risk simulations from on-chain verification. Gas is spent only when risk thresholds call for an on-chain record.

```
+-------------------------------------------------------------------------+
|                           Autonomous AI Agent                           |
|                    (Proposes DeFi position change)                      |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  Pre-Flight Risk Engine (risk_engine.py)                |
|  - Calculates projected health factor (HF)                              |
|  - Evaluates liquidation risk and assigns 0-100 risk score              |
|  - Classifies severity: Low, Medium, High, Critical                     |
+-------------------------------------------------------------------------+
                                    |
           +------------------------+------------------------+
           |                                                 |
           v [Severity < Medium / Score < 50]                v [Severity >= Medium / Score >= 50]
+---------------------------------------+   +---------------------------------------+
|          Off-Chain Pass-Through       |   |      Selective On-Chain Record        |
|  - Zero gas spent                     |   |  - RiskProof.logRiskEvent() called    |
|  - No on-chain log required           |   |  - Transaction committed on Arbitrum  |
|  - Safe action approved for execution |   |  - Permanent record stored on-chain   |
+---------------------------------------+   +---------------------------------------+
                                                             |
                                            +----------------+----------------+
                                            |                                 |
                                            v                                 v
                            +-------------------------------+ +-------------------------------+
                            |     Arbitrum Sepolia Log      | |  Telegram Alert (notifier.py) |
                            |  RiskProof Contract Storage   | |  - Severity badge and risk HF |
                            |  Permanent audit log on-chain | |  - Inline "View Proof" button |
                            +-------------------------------+ +-------------------------------+
```

---

## Repository Structure

- `contracts/RiskProof.sol`: Solidity contract recording on-chain risk events (`logRiskEvent`, `getRiskEvent`, `eventCount`).
- `risk_engine.py`: Core math calculating health factors, severity bands, and risk scores.
- `onchain_client.py`: Python Web3 client coordinating assessment and on-chain submission.
- `mcp_server.py`: FastMCP server exposing tools for autonomous AI agent runtimes.
- `notifier.py`: Telegram alert integration with HTML formatting and inline Arbiscan buttons.
- `test_pipeline.py`: Comprehensive in-memory EVM test suite using eth-tester and py-evm.
- `demo.py`: Live end-to-end demo testing Arbitrum Sepolia and Telegram dispatch.

---

## Setup

```bash
# Clone and install dependencies
npm install
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DEPLOYER_PRIVATE_KEY, RPC URL, and Telegram keys

# Compile Solidity contracts
npx hardhat compile
```

---

## Test Instructions

Run the test suites across smart contracts and the Python pipeline:

### 1. Smart Contract Tests
Run the Hardhat Mocha/Chai test suite:
```bash
npx hardhat test
```
Verifies event emission, storage retrieval, score validation (0-100), and boundary error handling.

### 2. In-Memory EVM Pipeline Tests
Run the end-to-end Python test suite against an in-memory EVM chain:
```bash
pytest -v test_pipeline.py
```
Or execute directly with Python:
```bash
python3 test_pipeline.py
```
Automatically deploys `RiskProof.sol` to an ephemeral in-memory EVM (`eth-tester`), verifies that Medium and higher severity actions are logged on-chain, confirms that low-risk actions bypass gas spending, and inspects stored event records.

---

## Live Demo (Arbitrum Sepolia)

Run the live pipeline demo against the deployed Arbitrum Sepolia contract:

```bash
python3 demo.py
```

This executes two simulated scenarios:
1. Risky Leverage Increase: Projected health factor drops below liquidation threshold; logs the assessment on Arbitrum Sepolia and sends a Telegram alert with an Arbiscan link.
2. Safe Collateral Addition: Projected health factor increases; marked as Low severity and execution continues with zero gas spent.

---

## FastMCP Server Integration

`mcp_server.py` provides a Model Context Protocol (MCP) server using FastMCP, allowing AI agents in environments like Claude Desktop, Cursor, and custom agent loops to evaluate risks autonomously.

### Available Tools

1. `simulate_risk`:
   - Fast, zero-gas pre-flight simulation.
   - Parameters: `agent_id`, `action_type`, `asset`, `current_collateral`, `current_debt`, `collateral_delta`, `debt_delta`.
   - Returns projected health factor, severity tier, 0-100 risk score, explanation reason, and `requires_onchain_proof` flag.

2. `evaluate_and_log_action`:
   - Evaluates action risk and automatically logs the assessment on Arbitrum Sepolia if severity is Medium or higher.
   - Dispatches a real-time Telegram alert with the transaction link upon confirmation.
   - Returns execution summary with transaction hash and Arbiscan URL.

3. `get_onchain_event_count`:
   - Reads the current total count of risk events logged on the `RiskProof` contract.

### Sample Client Configuration

Add this block to your MCP client configuration (such as `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "riskproof": {
      "command": "python3",
      "args": [
        "/path/to/riskproof/mcp_server.py"
      ],
      "env": {
        "ARBITRUM_SEPOLIA_RPC_URL": "https://sepolia-rollup.arbitrum.io/rpc",
        "DEPLOYER_PRIVATE_KEY": "your_private_key_here",
        "RISKPROOF_CONTRACT_ADDRESS": "0xA0046934fd8627695Ba76A879E421083C2487564",
        "TELEGRAM_BOT_TOKEN": "your_telegram_bot_token_here",
        "TELEGRAM_CHAT_ID": "your_telegram_chat_id_here"
      }
    }
  }
}
```

---

## Real-Time Alerts (Telegram)

`notifier.py` delivers instant alerts whenever a Medium or higher risk event is committed to Arbitrum Sepolia:
- Clean card layout with severity status (`🚨 CRITICAL`, `⚠️ HIGH`, `⚠️ MEDIUM`).
- Health factor metrics and liquidation warning badges.
- Sanitized HTML formatting preventing injection issues.
- Inline keyboard button linking directly to the Arbiscan transaction.
- Non-blocking error handling ensuring agent workflows proceed unimpeded if network notifications fail.

---

## Limitations (v1)

- Health factor math uses an Aave v3 style liquidation threshold (0.80) and fixed severity cutoffs, not live protocol parameters.
- `logRiskEvent()` is open to any caller. The `reporter` field records who wrote each entry, but v1 does not restrict who can log. An allowlist of authorized reporters is the next step.
- The log records the assessment. Blocking execution is up to the agent runtime calling Riskproof first.

---

## Contract Deployment and Verification

To deploy a new contract instance:

```bash
npx hardhat run scripts/deploy.js --network arbitrumSepolia
```

To verify the newly deployed contract on Arbiscan:

```bash
npx hardhat verify --network arbitrumSepolia <DEPLOYED_CONTRACT_ADDRESS>
```