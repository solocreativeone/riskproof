const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RiskProof", function () {
  let riskProof;

  beforeEach(async function () {
    const RiskProof = await ethers.getContractFactory("RiskProof");
    riskProof = await RiskProof.deploy();
    await riskProof.waitForDeployment();
  });

  it("logs a risk event and emits RiskLogged", async function () {
    const tx = await riskProof.logRiskEvent(
      "agent-001",
      "increase_leverage",
      3, // Severity.Critical
      100,
      "Projected health factor 0.94, below liquidation threshold"
    );

    await expect(tx)
      .to.emit(riskProof, "RiskLogged")
      .withArgs(
        0,
        await (await ethers.provider.getSigner()).getAddress(),
        "agent-001",
        3,
        100,
        "Projected health factor 0.94, below liquidation threshold",
        (await ethers.provider.getBlock("latest")).timestamp
      );

    expect(await riskProof.eventCount()).to.equal(1);
  });

  it("stores retrievable event data", async function () {
    await riskProof.logRiskEvent(
      "agent-001",
      "increase_leverage",
      3,
      100,
      "Critical severity test event"
    );

    const stored = await riskProof.getRiskEvent(0);
    expect(stored.agentId).to.equal("agent-001");
    expect(stored.severity).to.equal(3);
    expect(stored.riskScore).to.equal(100);
  });

  it("rejects a risk score above 100", async function () {
    await expect(
      riskProof.logRiskEvent("agent-001", "increase_leverage", 3, 150, "invalid score")
    ).to.be.revertedWith("riskScore must be 0-100");
  });

  it("reverts when reading an out-of-range event id", async function () {
    await expect(riskProof.getRiskEvent(0)).to.be.revertedWith("eventId out of range");
  });
});
