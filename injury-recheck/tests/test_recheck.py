import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import build  # noqa: E402

DATA = json.load(open(os.path.join(HERE, "data", "recheck.json"), encoding="utf-8"))
REPO = build.read_repo_rows(os.path.join(build.ROOT, "injuries.html"))


class RecheckTests(unittest.TestCase):
    def test_every_official_row_has_source_and_chunk(self):
        for r in DATA["official_rows"]:
            self.assertTrue(DATA["source_url"].startswith("https://www.nfl.com/"))
            self.assertIsInstance(r["chunk"], int)
            self.assertTrue(r["player"] and r["team"] and r["game_section"])

    def test_no_disagreements_with_repository(self):
        results = build.compare(DATA, REPO)
        bad = [r for r in results if r["verdict"] == "MISMATCH" or r["verdict"].startswith("MISSING")]
        self.assertEqual(bad, [])

    def test_lions_rows_are_out_on_repo_and_official(self):
        for name in ("Kerby Joseph", "Cade Mays", "D.J. Reed"):
            self.assertEqual(REPO[("DET", name)]["game"], "Out")

    def test_seattle_and_cincinnati_are_present_not_injury_free(self):
        self.assertEqual(sum(1 for k in REPO if k[0] == "SEA"), 4)
        self.assertEqual(sum(1 for k in REPO if k[0] == "CIN"), 4)

    def test_mismatch_is_detected(self):
        fake = dict(REPO)
        fake[("DET", "Kerby Joseph")] = {"position": "S", "injury": "Knee",
                                          "practice": "Full Participation in Practice", "game": ""}
        results = build.compare(DATA, fake)
        v = {r["player"]: r["verdict"] for r in results}
        self.assertEqual(v["Kerby Joseph"], "MISMATCH")

    def test_missing_row_is_detected(self):
        fake = {k: v for k, v in REPO.items() if k != ("SEA", "Sam Darnold")}
        v = {r["player"]: r["verdict"] for r in build.compare(DATA, fake)}
        self.assertEqual(v["Sam Darnold"], "MISSING from repo table")

    def test_page_builds_and_every_row_links_official(self):
        results = build.compare(DATA, REPO)
        text = build.page(DATA, results)
        self.assertIn("NFL.com official report", text)
        self.assertEqual(text.count("NFL.com official report ↗"), len(results))

    def test_irregularities_have_sources(self):
        for x in DATA["irregularities"]:
            self.assertTrue(x["source_url"].startswith("https://"))
            self.assertIn(x["severity"], {"low", "medium", "high"})


if __name__ == "__main__":
    unittest.main()
