// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title RiskProof
/// @notice Verifiable on-chain log of risky AI-agent actions in DeFi.
/// Medium+ severity risk assessments get written here so anyone can
/// verify the check happened, without trusting the off-chain service.
contract RiskProof {
    enum Severity {
        Low,
        Medium,
        High,
        Critical
    }

    struct RiskEvent {
        address reporter;
        string agentId;
        string actionType;
        Severity severity;
        uint256 riskScore; // 0-100, scaled by 100 for 2 decimals if needed later
        string reason;
        uint256 timestamp;
    }

    RiskEvent[] private events;

    event RiskLogged(
        uint256 indexed eventId,
        address indexed reporter,
        string agentId,
        Severity severity,
        uint256 riskScore,
        string reason,
        uint256 timestamp
    );

    /// @notice Logs a risk event on-chain. Intended to be called by the
    /// off-chain triage service once it decides an action is Medium+ severity.
    function logRiskEvent(
        string calldata agentId,
        string calldata actionType,
        Severity severity,
        uint256 riskScore,
        string calldata reason
    ) external returns (uint256 eventId) {
        require(riskScore <= 100, "riskScore must be 0-100");

        eventId = events.length;

        events.push(
            RiskEvent({
                reporter: msg.sender,
                agentId: agentId,
                actionType: actionType,
                severity: severity,
                riskScore: riskScore,
                reason: reason,
                timestamp: block.timestamp
            })
        );

        emit RiskLogged(
            eventId,
            msg.sender,
            agentId,
            severity,
            riskScore,
            reason,
            block.timestamp
        );
    }

    function getRiskEvent(uint256 eventId) external view returns (RiskEvent memory) {
        require(eventId < events.length, "eventId out of range");
        return events[eventId];
    }

    function eventCount() external view returns (uint256) {
        return events.length;
    }
}
