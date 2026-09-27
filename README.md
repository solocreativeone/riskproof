# Riskproof

Verifiable on-chain accountability layer for AI agents acting in DeFi.
Built for Colosseum's Crypto World's Fair.

## Status

- [x] Risk-scoring engine (`risk_engine.py`), done, tested locally
- [x] `RiskProof.sol` contract, written and compiled successfully with Hardhat
- [x] Hardhat test suite (`test/RiskProof.test.js`), all 4 tests passing:
      logging an event, reading it back, rejecting an invalid risk score,
      and rejecting an out-of-range read
- [ ] Deploy to Arbitrum Sepolia
- [ ] Wire risk engine output into `logRiskEvent()` call (Python -> chain)
- [ ] Stretch: MCP tool wrapper
- [ ] Stretch: Telegram alert

Note: the contract's read function is named `getRiskEvent`, not `getEvent`,
`getEvent` collides with a built-in method on ethers.js v6's Contract object.

## Setup

```bash
npm install
cp .env.example .env
# fill in DEPLOYER_PRIVATE_KEY (testnet wallet only) and RPC URL if not using the default
npx hardhat compile
npx hardhat test
```

## Deploy to Arbitrum Sepolia

```bash
npx hardhat run scripts/deploy.js --network arbitrumSepolia
```

Copy the deployed address, then verify on Arbiscan:

```bash
npx hardhat verify --network arbitrumSepolia <address>
```

## Next step

Deploy the contract to Arbitrum Sepolia testnet, then connect
`risk_engine.py`'s output to a `logRiskEvent()` transaction
(via ethers.js or web3.py) whenever severity is Medium or above.
