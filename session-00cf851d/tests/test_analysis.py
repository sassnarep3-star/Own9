"""Tests for the verification and replacement analysis."""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SESSION, "tools"))

import analysis  # noqa: E402

DATA = os.path.join(SESSION, "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


class TestVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = load("verification.json")

    def test_no_mismatches(self):
        bad = [c for c in self.v["checks"] if c["result"] == "mismatch"]
        self.assertEqual([], bad, "mismatched checks: %s" % [c["id"] for c in bad])

    def test_no_unverifiable(self):
        bad = [c for c in self.v["checks"] if c["result"] == "unverifiable"]
        self.assertEqual([], bad, "unverifiable checks: %s" % [c["id"] for c in bad])

    def test_every_check_names_a_source(self):
        for c in self.v["checks"]:
            self.assertTrue(c["source_url"].startswith("http"), c["id"])
            self.assertIn(c["source_id"], analysis.SOURCES, c["id"])

    def test_summary_totals_are_consistent(self):
        s = self.v["summary"]
        self.assertEqual(s["total_checks"], len(self.v["checks"]))
        self.assertEqual(s["match"] + s["mismatch"] + s["unverifiable"], s["total_checks"])

    def test_lineup_checks_cover_every_starting_slot(self):
        """All four elevens for both clubs, eleven slots each, two fields per slot."""
        lu = [c for c in self.v["checks"] if c["id"].startswith("LU-")]
        names = [c for c in lu if c["id"].endswith("-name")]
        self.assertEqual(11 * 4 * 2, len(names))

    def test_week10_final_score_is_verified(self):
        """The score the league prints is the score the repository committed."""
        fin = {c["id"]: c for c in self.v["checks"] if c["id"].startswith("FINAL-2026-REG10-WAS-NYG")}
        self.assertEqual(24, fin["FINAL-2026-REG10-WAS-NYG-WAS"]["value_read_from_official_source"])
        self.assertEqual(21, fin["FINAL-2026-REG10-WAS-NYG-NYG"]["value_read_from_official_source"])


class TestTranscription(unittest.TestCase):
    def test_league_points_for_equals_points_against(self):
        st = load("standings_2026.json")
        clubs = [c for d in st["divisions"] for c in d["clubs"]]
        self.assertEqual(32, len(clubs))
        self.assertEqual(sum(c["pf"] for c in clubs), sum(c["pa"] for c in clubs))

    def test_quarter_scores_sum_to_finals(self):
        for g in load("gamebooks.json")["games"]:
            for abbr, qs in g["quarters"].items():
                self.assertEqual(sum(qs), g["final"][abbr], g["game_id"])

    def test_eleven_starters_on_each_side(self):
        for g in load("gamebooks.json")["games"]:
            for abbr, block in g["teams"].items():
                self.assertEqual(11, len(block["offense_starters"]), (g["game_id"], abbr))
                self.assertEqual(11, len(block["defense_starters"]), (g["game_id"], abbr))

    def test_receiving_yards_do_not_exceed_passing_yards(self):
        for g in load("gamebooks.json")["games"]:
            for abbr, ind in g["individual"].items():
                rec = sum(r["yds"] for r in ind.get("receiving", []))
                pas = sum(p["yds"] for p in ind.get("passing", []))
                self.assertLessEqual(rec, pas, (g["game_id"], abbr))


class TestReplacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repl = load("replacement.json")

    def test_every_tier_is_derivable_from_the_game_books(self):
        """A tier must be reproducible from lists the league actually prints."""
        books = {g["game_id"]: g for g in load("gamebooks.json")["games"]}
        prior = {"WAS": "2026-REG9-LAR-WAS", "NYG": "2026-REG9-NYG-PHI"}
        for r in self.repl["rows"]:
            if not r["provenance_tier"]:
                continue
            block = books[prior[r["club"]]]["teams"][r["club"]]
            surname = analysis._surname(r["replacement"])
            found = None
            for tier, key in (("T1", "offense_starters"), ("T1", "defense_starters"),
                              ("T2", "substitutions"), ("T2", "did_not_play"),
                              ("T3", "not_active")):
                entries = block[key]
                if key.endswith("_starters"):
                    entries = [n for _, n in entries]
                if any(analysis._surname(e) == surname for e in entries):
                    found = tier
                    break
            self.assertEqual(r["provenance_tier"], found or "T4", r)

    def test_tier_counts_add_up(self):
        counts = self.repl["tier_counts"]
        self.assertEqual(self.repl["n_replacements_measured"], sum(counts.values()))

    def test_the_inactive_list_replacement_is_real(self):
        """Nick Allegretti was on the Week 9 substitution list, not the inactive list."""
        rows = [r for r in self.repl["rows"] if r["replacement"] == "67 N.Allegretti"]
        self.assertEqual(1, len(rows))
        self.assertEqual("T2", rows[0]["provenance_tier"])
        self.assertIn("substitution", rows[0]["week9_status"].lower())

    def test_no_row_claims_a_depth_chart_tier(self):
        text = json.dumps(self.repl)
        for phrase in ("2nd string", "3rd string", "4th string", "second string",
                       "third string", "fourth string"):
            self.assertNotIn(phrase, text.lower())


class TestResultsAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = load("results_audit.json")

    def test_no_fair_line_is_invented(self):
        for m in self.a["market_vs_outcome_2026"]["rows"]:
            self.assertIsNone(m["model_fair_line"])
            self.assertIsNone(m["model_fair_total"])

    def test_internal_arithmetic_passes(self):
        ic = self.a["internal_consistency"]
        self.assertEqual(0, ic["rows_where_that_fails"])

    def test_convention_correlation_is_positive(self):
        self.assertGreater(self.a["convention"]["correlation"], 0)
        self.assertGreater(self.a["convention"]["n_pairs"], 5000)

    def test_two_clubs_reconcile_with_the_league(self):
        rec = [c for c in self.a["club_reconciliation"]["clubs"] if c["reconciles"]]
        self.assertEqual(2, len(rec))
        self.assertEqual({"PIT", "TEN"}, {c["abbr"] for c in rec})

    def test_pittsburgh_matches_the_official_standings_exactly(self):
        pit = next(c for c in self.a["club_reconciliation"]["clubs"] if c["abbr"] == "PIT")
        self.assertEqual((6, 2, 0, 180, 144), (pit["recomputed_w"], pit["recomputed_l"],
                                               pit["recomputed_t"], pit["recomputed_pf"],
                                               pit["recomputed_pa"]))
        self.assertEqual((6, 2, 0, 180, 144), (pit["official_w"], pit["official_l"],
                                               pit["official_t"], pit["official_pf"],
                                               pit["official_pa"]))

    def test_missing_results_are_the_most_recent_games(self):
        cc = self.a["current_season_completeness"]
        self.assertEqual(16, cc["of_those_missing_a_result"])
        self.assertIn("2026_10_WAS_NYG", cc["missing_game_ids"])

    def test_official_outcomes_are_none_of_them_in_the_file(self):
        """The gap this session filled was a real gap, not a join bug."""
        rows = self.a["officially_verified_outcomes"]["rows"]
        self.assertTrue(rows)
        self.assertEqual(0, sum(1 for r in rows if r["result_present_in_committed_file"]))


class TestRegisters(unittest.TestCase):
    def test_every_flag_carries_at_least_one_source(self):
        for f in load("flags.json")["flags"]:
            self.assertTrue(f["source_url"].startswith("http"), f["id"])
            self.assertTrue(f["what_was_observed"] and f["why_it_matters"]
                            and f["what_this_session_did"], f["id"])

    def test_every_question_carries_a_source_and_a_status(self):
        allowed = {"answered", "open-decision", "open-source", "probe"}
        for q in load("questions.json")["questions"]:
            self.assertIn(q["status"], allowed, q["id"])
            self.assertTrue(q["source_url"].startswith("http"), q["id"])
            self.assertTrue(q["what_we_have"] and q["what_is_missing"], q["id"])

    def test_every_suggestion_offers_at_least_one_path_and_a_decision(self):
        for s in load("suggestions.json")["suggestions"]:
            self.assertTrue(s["paths"], s["id"])
            self.assertTrue(s["decision_needed"], s["id"])
            for p in s["paths"]:
                self.assertTrue(p["cost"] and p["risk"] and p["unblocks"], p["id"])

    def test_every_source_entry_is_official_and_dated(self):
        for s in load("sources.json")["sources"]:
            self.assertTrue(s["official"], s["id"])
            self.assertEqual("2026-11-14", s["retrieved_utc"])
            self.assertTrue(s["url"].startswith("https://"), s["id"])


if __name__ == "__main__":
    unittest.main()
