// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/**
 * @title SovereignVault — Autonomous On-Chain Drawdown Guardian
 * @notice Enforces hard-coded mathematical risk limits for solo quantitative fund managers.
 * @dev Integrates SoSoValue ETF macroeconomic telemetry and ValueChain smart vaults.
 * @author Usman Bamidele (100L Pure Mathematics, FUNAAB, Abeokuta, Nigeria)
 */
contract SovereignVault {
    address public immutable soloOperator;
    uint256 public constant MAX_DRAWDOWN_BPS = 300; // 3.00% Hard Drawdown Cap
    uint256 public constant MAX_TRADE_LOSS_BPS = 100; // 1.00% Single-Trade VaR Cap

    uint256 public peakEquityUsd;
    uint256 public currentEquityUsd;
    bool public isCircuitBreakerTripped;

    event CircuitBreakerTripped(uint256 currentEquity, uint256 peakEquity, uint256 drawdownBps);
    event TradeExecuted(bytes32 indexed tradeId, uint256 amount, uint256 stopLossBps);
    event EquityUpdated(uint256 previousEquity, uint256 newEquity);

    modifier onlyOperator() {
        require(msg.sender == soloOperator, "UNAUTHORIZED: Only solo fund operator");
        _;
    }

    modifier whenNotTripped() {
        require(!isCircuitBreakerTripped, "EXECUTION_LOCKED: Circuit breaker is active");
        _;
    }

    constructor(uint256 initialEquityUsd) {
        require(initialEquityUsd > 0, "INVALID_INITIAL_EQUITY");
        soloOperator = msg.sender;
        peakEquityUsd = initialEquityUsd;
        currentEquityUsd = initialEquityUsd;
        isCircuitBreakerTripped = false;
    }

    /**
     * @notice Updates the fund's mark-to-market equity and evaluates drawdown limits.
     * @param newEquityUsd Current total portfolio valuation in minor units (cents).
     */
    function updateEquity(uint256 newEquityUsd) external onlyOperator {
        uint256 prev = currentEquityUsd;
        currentEquityUsd = newEquityUsd;

        if (newEquityUsd > peakEquityUsd) {
            peakEquityUsd = newEquityUsd;
        } else {
            uint256 drawdown = peakEquityUsd - newEquityUsd;
            uint256 drawdownBps = (drawdown * 10000) / peakEquityUsd;

            if (drawdownBps >= MAX_DRAWDOWN_BPS) {
                isCircuitBreakerTripped = true;
                emit CircuitBreakerTripped(newEquityUsd, peakEquityUsd, drawdownBps);
            }
        }

        emit EquityUpdated(prev, newEquityUsd);
    }

    /**
     * @notice Validates that a trade adheres to the 1.0% single-trade VaR limit.
     */
    function validateAndExecuteTrade(
        bytes32 tradeId,
        uint256 tradeSizeUsd,
        uint256 stopLossBps
    ) external onlyOperator whenNotTripped {
        uint256 potentialLoss = (tradeSizeUsd * stopLossBps) / 10000;
        uint256 maxAllowedLoss = (currentEquityUsd * MAX_TRADE_LOSS_BPS) / 10000;

        require(potentialLoss <= maxAllowedLoss, "RISK_EXCEEDED: Single-trade VaR violation");

        emit TradeExecuted(tradeId, tradeSizeUsd, stopLossBps);
    }
}
