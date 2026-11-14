"""Tests for the ledger stores and rules. Synthetic inputs are labelled as such."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ledger as L  # noqa: E402


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.results = L.load_csv("results_verified.csv")
        self.prices = L.load_csv("price_snapshots.csv")
        self.reps = L.load_csv("replacements.csv")

    def test_results_are_final_official_and_valid(self):
        self.assertEqual(len(self.results), 16)
        self.assertEqual(L.validate_results(self.results), [])
        self.assertEqual({int(r["week"]) for r in self.results}, {9, 10})
        self.assertEqual(sum(1 for r in self.results if r["week"] == "9"), 15)

    def test_results_match_sibling_game_book_evidence(self):
        ev = json.loads((ROOT / "evidence/lineups/was-nyg-2026-week-9-10.json").read_text())
        finals = {g["id"]: g["final"] for g in ev["games"]}
        by_id = {r["game_id"]: r for r in self.results}
        mapping = {"2026-REG9-LAR-WAS": "2026-REG9-LA-WAS", "2026-REG9-NYG-PHI": "2026-REG9-NYG-PHI",
                   "2026-REG10-WAS-NYG": "2026-REG10-WAS-NYG"}
        for ev_id, ledger_id in mapping.items():
            row = by_id[ledger_id]
            away = {"2026-REG9-LAR-WAS": "LA", "2026-REG9-NYG-PHI": "NYG", "2026-REG10-WAS-NYG": "WAS"}[ev_id]
            self.assertEqual(int(row["away_score"]), finals[ev_id]["away"], ledger_id)
            self.assertEqual(int(row["home_score"]), finals[ev_id]["home"], ledger_id)
            self.assertEqual(row["away"], away)

    def test_results_reject_non_official_host_and_non_final(self):
        bad = dict(self.results[0], source_url="https://example.com/x")
        self.assertTrue(any("official host" in e for e in L.validate_results([bad])))
        bad2 = dict(self.results[0], status="Scheduled")
        self.assertTrue(any("final" in e for e in L.validate_results([bad2])))

    def test_prices_follow_origination_order_and_market_source(self):
        self.assertEqual(len(self.prices), 48)
        self.assertEqual(len({r["game_id"] for r in self.prices}), 8)
        self.assertEqual(L.validate_prices(self.prices), [])
        for r in self.prices:
            self.assertEqual(L.ORDER[r["market"]], int(r["origination_order"]))
            self.assertEqual(L.host(r["market_source_url"]), "sportsbook.draftkings.com")
            # Non-official DraftKings values are withheld: no line or price, and the row is flagged unverified.
            self.assertEqual((r["line"], r["american_odds"]), ("", ""))
            self.assertTrue(r["verification_status"].startswith("Unverified"))

    def test_no_open_or_close_value_without_source_and_timestamp(self):
        for r in self.prices:
            self.assertEqual(r["open_line"], "")
            self.assertEqual(r["open_odds"], "")
            self.assertEqual(r["close_line"], "")
            self.assertEqual(r["close_odds"], "")

    def test_price_validation_rejects_open_value_without_timestamp(self):
        bad = dict(self.prices[0], open_line="+2.5", open_time_utc="")
        self.assertTrue(any("without a timestamp" in e for e in L.validate_prices([bad])))

    def test_price_validation_rejects_wrong_order(self):
        bad = dict(self.prices[0], origination_order="3")
        self.assertTrue(any("origination_order" in e for e in L.validate_prices([bad])))

    def test_replacements_have_no_depth_tiers_and_official_links(self):
        self.assertEqual(len(self.reps), 12)
        self.assertEqual(L.validate_replacements(self.reps), [])
        self.assertTrue(all(not r["depth_tier_out"] and not r["depth_tier_in"] for r in self.reps))

    def test_replacement_chain_is_present_and_documented(self):
        chain = [r for r in self.reps if r["player_out"] == "63 L.Patrick"]
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["player_in"], "67 N.Allegretti")
        self.assertEqual(chain[0]["injury_wk10"], "Concussion")

    def test_coverage_counts_match_stores(self):
        cov = L.coverage(self.results, self.prices, self.reps, {f"C0{i}": 0 for i in range(1, 9)})
        self.assertEqual(cov["verified_results"], 16)
        self.assertEqual(cov["price_rows"], 48)
        self.assertEqual(cov["open_values"], 0)
        self.assertEqual(cov["fair_lines"], 0)
        self.assertEqual(cov["correlation_coefficients"], 0)
        self.assertEqual(cov["depth_tiers_published"], 0)

    def test_every_policy_source_is_registered(self):
        srcs = L.load_json("sources.json")["sources"]
        self.assertTrue(all(s["url"].startswith("https://") for s in srcs))
        ids = {s["id"] for s in srcs}
        q = L.load_json("questions.json")["items"]
        s = L.load_json("suggestions.json")["items"]
        f = L.load_json("flags.json")["items"]
        for item in q + s + f:
            for sid in item.get("source_ids", item.get("sources", [])):
                if sid in {"SK-CV", "SK-TIME", "SK-CAL", "SP-R", "SP-BOOT", "DK-GENERAL", "DK-MARKETS"}:
                    continue  # defined in research/catalog.json
                self.assertIn(sid, ids, f"{item['id']} cites unknown source {sid}")


class DemotionAndLeaderboardTests(unittest.TestCase):
    CLEAR = dict(provenance_ok=True, asof_ok=True, n_forecasts=500, ll_diff_lower=-0.01, n_bin_breaches=0,
                 n_priced=500, clv_upper=0.02, dep_n=100, dep_outside_band=False, joint_fail=False,
                 max_drawdown=0.1, drawdown_cap=0.2, stake_rule_ok=True)

    def test_missing_inputs_are_not_evaluated_and_never_clear(self):
        states = L.evaluate_demotion({})
        self.assertTrue(all(v == "not evaluated" for v in states.values()))
        self.assertFalse(L.may_stay_live(states))

    def test_all_clear_inputs_keep_a_strategy_live(self):
        # Synthetic input for the rule check only; not a result for any real strategy.
        states = L.evaluate_demotion(self.CLEAR)
        self.assertEqual(set(states.values()), {"clear"})
        self.assertTrue(L.may_stay_live(states))

    def test_signal_breach_demotes_even_with_excellent_staking(self):
        # Synthetic: signal log loss worse than market with a CI above zero, but ROI and drawdown are great.
        m = dict(self.CLEAR, ll_diff_lower=0.004, max_drawdown=0.01, drawdown_cap=0.2)
        states = L.evaluate_demotion(m)
        self.assertEqual(states["D2"], "breach")
        self.assertFalse(L.may_stay_live(states))

    def test_insufficient_sample_is_not_cleared_by_default(self):
        m = dict(self.CLEAR, n_forecasts=50, ll_diff_lower=-0.5)
        self.assertEqual(L.evaluate_demotion(m)["D2"], "not evaluated")

    def test_provenance_breach_is_immediate(self):
        m = dict(self.CLEAR, provenance_ok=False)
        self.assertEqual(L.evaluate_demotion(m)["D1"], "breach")

    def test_staking_breach_demotes_even_with_clear_signal(self):
        m = dict(self.CLEAR, max_drawdown=0.5, drawdown_cap=0.2)
        self.assertEqual(L.evaluate_demotion(m)["D6"], "breach")

    def test_signal_rank_ignores_staking_and_requires_all_signal_gates(self):
        gates_pass = {f"G0{i}": "pass" for i in range(1, 10)}
        gates_fail = dict(gates_pass, G05="not evaluated")
        strategies = [
            # Synthetic: best staking, weak signal, one gate not evaluated -> must not rank.
            {"id": "LUCKY", "gate_status": gates_fail, "signal_score": 0.9, "roi": 5.0},
            {"id": "SKILL", "gate_status": gates_pass, "signal_score": 0.4, "roi": -0.1},
            {"id": "STEADY", "gate_status": gates_pass, "signal_score": 0.5, "roi": 9.0},
        ]
        ranked = L.rank_signal(strategies)
        self.assertEqual([r["id"] for r in ranked], ["SKILL", "STEADY"])
        # Staking view is informational: it orders by ROI, but LUCKY stays out of the signal ranking.
        self.assertEqual([r["id"] for r in L.rank_staking_informational(strategies)][0], "STEADY")
        self.assertNotIn("LUCKY", [r["id"] for r in ranked])

    def test_catalog_strategies_are_unranked_today(self):
        cat = json.loads((ROOT / "research/catalog.json").read_text())
        gates = {g["id"]: g["status"] for g in cat["gates"]}
        self.assertEqual(len(gates), 11)
        strategies = [{"id": s["id"], "gate_status": {}, "signal_score": None} for s in cat["strategies"]]
        self.assertEqual(L.rank_signal(strategies), [])


class CorrelationRuleTests(unittest.TestCase):
    def test_zero_n_publishes_n_and_no_coefficient(self):
        out = L.publish_correlation(None, 0, True, None)
        self.assertEqual(out["n"], 0)
        self.assertIsNone(out["r"])
        self.assertIn("no paired official", out["status"])

    def test_small_n_hides_coefficient(self):
        out = L.publish_correlation(0.4, 12, True, (0.1, 0.6))
        self.assertEqual(out["n"], 12)
        self.assertIsNone(out["r"])

    def test_unofficial_pairs_hide_coefficient(self):
        out = L.publish_correlation(0.4, 200, False, (0.2, 0.5))
        self.assertIsNone(out["r"])
        self.assertIn("unofficial", out["status"])

    def test_official_large_n_with_interval_publishes(self):
        # Synthetic inputs to test the rule only.
        out = L.publish_correlation(0.41234, 120, True, (0.2, 0.6))
        self.assertEqual(out["r"], 0.4123)
        self.assertEqual(out["status"], "published")

    def test_catalog_pairs_all_have_zero_official_n(self):
        pairs = L.load_catalog_correlations()
        self.assertEqual(len(pairs), 8)
        for p in pairs:
            self.assertIsNone(p["pearson_r"])


if __name__ == "__main__":
    unittest.main()
