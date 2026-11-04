import json
from pathlib import Path
import unittest
from engine.report import report

ROOT=Path(__file__).resolve().parents[1]
class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'research/catalog.json').read_text())
    def test_sources(self):
        sources=self.data['sources']
        self.assertEqual(len({s['id'] for s in sources}),len(sources))
        for s in sources:
            self.assertTrue(s['url'].startswith('https://'))
            self.assertIn(s['status'],['checked','unverified'])
            if s['status']=='checked':
                self.assertTrue(s['evidence'])
                self.assertEqual(s['checked_on'],'2026-11-04')
    def test_every_row_has_source(self):
        ids={s['id'] for s in self.data['sources']}
        for key in ['strategies','gates','correlations','flags','observations','requirements','audit']:
            seen=set()
            for row in self.data[key]:
                self.assertNotIn(row['id'],seen)
                seen.add(row['id'])
                self.assertTrue(row['source_ids'])
                self.assertTrue(set(row['source_ids']) <= ids)
    def test_no_fabricated_metrics(self):
        for s in self.data['strategies']:
            for key in ['rank','roi','brier','log_loss','n_bets','reward']:
                self.assertIsNone(s[key])
        for c in self.data['correlations']:
            for key in ['pearson_r','ci_low','ci_high','n_pairs']:
                self.assertIsNone(c[key])
    def test_report_abstains(self):
        out=report(self.data)
        self.assertEqual(out['eligible_count'],0)
        self.assertEqual(len(out['strategies']),8)
        for s in out['strategies']:
            self.assertFalse(s['eligible'])
            self.assertEqual(len(s['blockers']),11)
            self.assertIsNone(s['roi'])
            self.assertIsNone(s['rank'])
    def test_site_manifest_matches(self):
        self.assertEqual(self.data,json.loads((ROOT/'site/data/catalog.json').read_text()))

if __name__=='__main__': unittest.main()
