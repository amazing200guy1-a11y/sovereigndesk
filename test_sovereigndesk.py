"""
Formal Invariant & Latency Benchmark Suite for SovereignDesk
Platform: SoSoValue Open Platform & ValueChain Smart Vaults
Author: Usman Bamidele (100L Pure Mathematics, FUNAAB, Abeokuta, Nigeria)
Copyright (c) 2026 Usman Bamidele · Zero External Dependencies (Python 3 stdlib unittest)
"""

import unittest
import time
from sovereigndesk_engine import SovereignDeskEngine, RiskStatus

class TestSovereignDeskFormalInvariants(unittest.TestCase):
    def setUp(self):
        self.engine = SovereignDeskEngine(
            portfolio_equity_usd=25_000_000.0,
            max_drawdown_limit_pct=3.0,
            single_trade_max_loss_pct=1.0
        )

    def test_01_parametric_var_99_confidence(self):
        """Invariant 1: 99% VaR must strictly equal z * sigma * equity."""
        equity = 25_000_000.0
        daily_vol_pct = 3.0
        var_usd, var_pct, cvar_usd = self.engine.compute_parametric_var(
            equity=equity,
            daily_volatility_pct=daily_vol_pct,
            confidence_level=0.99,
            horizon_days=1
        )
        self.assertAlmostEqual(var_pct, 6.97904, places=2)
        self.assertGreater(cvar_usd, var_usd, "CVaR must strictly exceed VaR in the loss tail")

    def test_02_expected_shortfall_tail_monotonicity(self):
        """Invariant 2: Expected Shortfall (CVaR) increases monotonically with confidence."""
        equity = 10_000_000.0
        _, _, cvar_95 = self.engine.compute_parametric_var(equity, 2.5, 0.95, 1)
        _, _, cvar_99 = self.engine.compute_parametric_var(equity, 2.5, 0.99, 1)
        _, _, cvar_999 = self.engine.compute_parametric_var(equity, 2.5, 0.999, 1)

        self.assertLess(cvar_95, cvar_99)
        self.assertLess(cvar_99, cvar_999)

    def test_03_etf_macro_beta_directionality(self):
        """Invariant 3: Positive correlation with Spot ETF inflows produces positive Beta."""
        asset_returns = [0.02, 0.04, -0.01, 0.03, -0.02]
        etf_inflows = [100_000_000, 250_000_000, -50_000_000, 180_000_000, -120_000_000]
        beta = self.engine.compute_etf_macro_beta(asset_returns, etf_inflows)
        self.assertGreater(beta, 0.0, "Asset moving with ETF inflows must exhibit positive beta")

    def test_04_circuit_breaker_normal_state(self):
        """Invariant 4: Normal equity fluctuations within 2.0% drawdown do not trip breaker."""
        status, dd_pct, is_tripped = self.engine.evaluate_circuit_breaker(current_equity_usd=24_600_000.0)
        self.assertEqual(status, RiskStatus.NORMAL)
        self.assertFalse(is_tripped)
        self.assertAlmostEqual(dd_pct, 1.6, places=1)

    def test_05_circuit_breaker_warning_zone(self):
        """Invariant 5: Drawdown between 2.25% and 2.99% flags WARNING state."""
        status, dd_pct, is_tripped = self.engine.evaluate_circuit_breaker(current_equity_usd=24_350_000.0)
        self.assertEqual(status, RiskStatus.WARNING)
        self.assertFalse(is_tripped)

    def test_06_circuit_breaker_hard_trip(self):
        """Invariant 6: Drawdown >= 3.0% immediately trips autonomous circuit breaker."""
        status, dd_pct, is_tripped = self.engine.evaluate_circuit_breaker(current_equity_usd=24_200_000.0)
        self.assertEqual(status, RiskStatus.CIRCUIT_BREAKER_TRIPPED)
        self.assertTrue(is_tripped)
        self.assertTrue(self.engine.circuit_breaker_active)

    def test_07_execution_rejection_when_circuit_breaker_tripped(self):
        """Invariant 7: All new trade executions are blocked when circuit breaker is active."""
        self.engine.circuit_breaker_active = True
        approved, reason = self.engine.validate_trade_execution(
            trade_size_usd=100_000.0,
            stop_loss_pct=2.0,
            current_equity_usd=24_000_000.0
        )
        self.assertFalse(approved)
        self.assertIn("EXECUTION_HALTED", reason)

    def test_08_single_trade_loss_cap_enforcement(self):
        """Invariant 8: Single trade with potential loss > 1.0% equity is rejected."""
        approved, reason = self.engine.validate_trade_execution(
            trade_size_usd=10_000_000.0,
            stop_loss_pct=3.0,
            current_equity_usd=25_000_000.0
        )
        self.assertFalse(approved)
        self.assertIn("RISK_VIOLATION", reason)

    def test_09_single_trade_loss_cap_approval(self):
        """Invariant 9: Trade with potential loss <= 1.0% equity is approved."""
        approved, reason = self.engine.validate_trade_execution(
            trade_size_usd=2_000_000.0,
            stop_loss_pct=2.0,
            current_equity_usd=25_000_000.0
        )
        self.assertTrue(approved)
        self.assertIn("APPROVED", reason)

    def test_10_ai_token_pruning_optimization(self):
        """Invariant 10: Quantitative parser prunes raw conversational prompt by > 80%."""
        verbose_prompt = (
            "Autonomous Market Agent evaluating real-time order execution. Please look at current market feeds "
            "and execute a BUY order for 500,000 USD of Bitcoin BTC on ValueChain DEX with a stop-loss at 1.5% "
            "because institutional Spot ETF net inflows just surged according to SoSoValue telemetry."
        )
        compact, raw_tok, pruned_tok, reduction = self.engine.prune_agent_prompt_tokens(verbose_prompt)
        self.assertIn("ACTION:BUY", compact)
        self.assertIn("PAIR:BTC", compact)
        self.assertGreaterEqual(reduction, 80.0, f"Token reduction ({reduction:.1f}%) must be >= 80%")

    def test_11_hallucination_firewall_rejects_unconserved_allocation(self):
        """Invariant 11: Hallucinated portfolio allocation summing to 110% is blocked."""
        hallucinated_portfolio = {"BTC": 40.0, "ETH": 35.0, "SOL": 35.0} # Sums to 110%
        valid, reason = self.engine.verify_agent_hallucination_firewall(hallucinated_portfolio)
        self.assertFalse(valid)
        self.assertIn("HALLUCINATION_DETECTED", reason)

    def test_12_hallucination_firewall_approves_conserved_allocation(self):
        """Invariant 12: Strictly conserved 100% allocation with concentration caps passes."""
        valid_portfolio = {"BTC": 35.0, "ETH": 30.0, "SOL": 20.0, "USDC": 15.0} # Sums to 100%
        valid, reason = self.engine.verify_agent_hallucination_firewall(valid_portfolio)
        self.assertTrue(valid)
        self.assertIn("PASSED", reason)

    def test_13_sub_millisecond_latency_benchmark(self):
        """Invariant 13: Full risk and invariant cycle executes in under 0.05 ms/op."""
        iterations = 500
        start = time.perf_counter()
        for _ in range(iterations):
            self.engine.compute_parametric_var(25_000_000.0, 3.2, 0.99, 1)
            self.engine.evaluate_circuit_breaker(24_800_000.0)
            self.engine.validate_trade_execution(1_000_000.0, 1.5, 25_000_000.0)
            self.engine.verify_agent_hallucination_firewall({"BTC": 35.0, "ETH": 30.0, "SOL": 20.0, "USDC": 15.0})
        elapsed = time.perf_counter() - start
        avg_latency_ms = (elapsed / (iterations * 4)) * 1000.0

        self.assertLess(avg_latency_ms, 0.05)
        print(f"\n[BENCHMARK] {iterations * 4} SovereignDesk Invariant Operations: {elapsed:.4f}s | Avg Latency: {avg_latency_ms:.4f} ms/operation")

if __name__ == "__main__":
    unittest.main()
