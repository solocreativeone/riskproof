const hre = require("hardhat");

async function main() {
  const RiskProof = await hre.ethers.getContractFactory("RiskProof");
  const contract = await RiskProof.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("RiskProof deployed to:", address);
  console.log("Verify with:");
  console.log(`  npx hardhat verify --network arbitrumSepolia ${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
