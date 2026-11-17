"""Regression tests for the Week 10 availability re-count (session 6669951c).

These tests re-run the generator against the committed artefacts. They assert the numbers the
team availability page publishes, the fail-closed behaviour of the tool, and the discipline rules
the page is built on: a blank game status is never read as availability, an unretained claim is
never repaired with an estimate, and no depth tier or performance effect is asserted.
"""
import importlib.util
import json
import re
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


def _load():
    spec = importlib.util.spec_from_file_location(
        'recount_6669951c', ROOT / 'session-6669951c/tools/recount.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECOUNT = _load()
ARTIFACT = json.loads((ROOT / 'session-6669951c/data/week-10-availability-recount.json').read_text())


class TestArtefactIdentity(unittest.TestCase):
    def test_capture_hash_still_matches_its_manifest(self):
        identity = RECOUNT.check_artefact_identity()
        self.assertEqual(identity['id'], 'CAP-01')
        self.assertEqual(identity['url'], 'https://www.nfl.com/injuries/')
        self.assertEqual(len(identity['sha256']), 64)
        self.assertGreater(identity['bytes'], 40000)

    def test_a_tampered_capture_fails_closed(self):
        tampered = pathlib.Path(tempfile.gettempdir()) / 'tampered-capture.md'
        text = RECOUNT.CAPTURE.read_text().replace('Kerby Joseph', 'Kerby Josephx', 1)
        tampered.write_text(text)
        original = RECOUNT.CAPTURE
        try:
            RECOUNT.CAPTURE = tampered
            with self.assertRaises(RECOUNT.RecountError):
                RECOUNT.check_artefact_identity()
        finally:
            RECOUNT.CAPTURE = original
            tampered.unlink()

    def test_generated_json_is_not_stale(self):
        self.assertEqual(
            json.dumps(RECOUNT.compute(), indent=1, sort_keys=True) + '\n',
            ARTIFACT_TEXT, 'the committed recount artefact does not match its inputs')


ARTIFACT_TEXT = (ROOT / 'session-6669951c/data/week-10-availability-recount.json').read_text()


class TestCounts(unittest.TestCase):
    def setUp(self):
        self.tot = ARTIFACT['totals']

    def test_slate_and_tables_are_complete(self):
        self.assertEqual(self.tot['games_listed'], 14)
        self.assertEqual(self.tot['club_tables'], 28)
        self.assertEqual(self.tot['club_headers'], 28)
        self.assertEqual(self.tot['club_headers_without_table'], [])

    def test_published_counts(self):
        self.assertEqual(self.tot['rows'], 347)
        self.assertEqual(self.tot['out'], 70)
        self.assertEqual(self.tot['doubtful'], 11)
        self.assertEqual(self.tot['questionable'], 90)
        self.assertEqual(self.tot['explicit_game_status'], 171)
        self.assertEqual(self.tot['blank_game_status'], 176)

    def test_designations_partition_the_rows_exactly(self):
        self.assertEqual(self.tot['out'] + self.tot['doubtful'] + self.tot['questionable']
                         + self.tot['blank_game_status'], self.tot['rows'])
        self.assertEqual(self.tot['dnp'] + self.tot['limited'] + self.tot['full'], self.tot['rows'])
        self.assertEqual(self.tot['positions_unclassified'], 0)

    def test_a_blank_status_is_never_counted_as_available(self):
        for club in ARTIFACT['clubs']:
            self.assertEqual(club['out'] + club['doubtful'] + club['questionable']
                             + club['practice_only'], club['listed'], club['club'])
            self.assertEqual(club['confirmed_unavailable'], club['out'] + club['doubtful'])
            self.assertEqual(club['conditional'], club['questionable'])

    def test_the_root_page_understates_the_capture_by_the_monday_night_pair(self):
        # Published figure vs the capture, computed rather than asserted from prose.
        self.assertEqual(ARTIFACT['transcription']['rows'], 160)
        self.assertEqual(self.tot['explicit_game_status'] - ARTIFACT['transcription']['rows'], 11)


class TestDelta(unittest.TestCase):
    def test_real_additions_are_the_two_unpublished_clubs(self):
        diff = ARTIFACT['diff']
        added = diff['join_by_name']['added']
        artefacts = {a['player_id'] for a in diff['name_spelling_artefacts']}
        real = [a for a in added if a['player_id'] not in artefacts]
        self.assertEqual(len(real), 12)
        self.assertEqual({a['club'] for a in real}, {'LAC', 'BAL'})
        self.assertEqual(sum(1 for a in real if a['club'] == 'LAC'), 10)
        self.assertEqual(sum(1 for a in real if a['club'] == 'BAL'), 2)

    def test_no_designation_level_changed_and_one_row_disappeared(self):
        diff = ARTIFACT['diff']
        self.assertEqual(diff['join_by_name']['changed'], [])
        removed = diff['join_by_name']['removed']
        self.assertEqual(len(removed), 3)          # by name
        self.assertEqual(len([r for r in removed
                             if r['player'] not in {a['transcribed_name']
                                                    for a in diff['name_spelling_artefacts']}]), 1)

    def test_the_join_artefacts_are_published_not_silently_merged(self):
        pairs = {(a['capture_name'], a['transcribed_name']) for a in
                 ARTIFACT['diff']['name_spelling_artefacts']}
        self.assertEqual(pairs, {('Jacob Hummel', 'Jake Hummel'), ('Kam Curl', 'Kamren Curl')})
        self.assertEqual(ARTIFACT['diff']['per_club'], sorted(
            ARTIFACT['diff']['per_club'], key=lambda p: p['club']))


class TestPointInTime(unittest.TestCase):
    def test_most_of_the_week_had_already_kicked_off(self):
        games = ARTIFACT['games']
        self.assertEqual(len(games), 14)
        after = [g for g in games if g['state'] == 'after kickoff']
        self.assertEqual(len(after), 12)
        self.assertTrue(all(g['minutes_from_capture'] < 0 for g in after))

    def test_pre_kickoff_blocks_are_positive_and_the_margin_is_small(self):
        pre = [g for g in ARTIFACT['games'] if g['state'] == 'before kickoff']
        # The report lists the away club first, and the tool preserves that order.
        self.assertEqual({tuple(g['clubs']) for g in pre}, {('LAC', 'BAL'), ('PIT', 'CIN')})
        self.assertTrue(all(g['minutes_from_capture'] > 0 for g in pre))
        self.assertEqual(min(abs(g['minutes_from_capture']) for g in ARTIFACT['games']), 2)

    def test_rows_are_reconciled_across_the_game_table(self):
        self.assertEqual(sum(g['rows'] for g in ARTIFACT['games']), ARTIFACT['totals']['rows'])


class TestRosterEvents(unittest.TestCase):
    def test_join_counts(self):
        tx = ARTIFACT['transactions']
        self.assertEqual(tx['trades'], 12)
        self.assertEqual(tx['reserve_list_rows'], 25)
        self.assertEqual(tx['events_total'], 37)
        self.assertEqual(len(tx['matches']), 13)
        self.assertEqual(len(tx['events_not_on_report']), 24)
        self.assertEqual(len(tx['matches']) + len(tx['events_not_on_report']), 37)

    def test_the_two_conflict_classes_exist(self):
        kinds = {}
        for m in ARTIFACT['transactions']['matches']:
            head = m['classification'].split('—')[0].strip()
            kinds[head] = kinds.get(head, 0) + 1
        self.assertEqual(kinds['stale'], 1)
        self.assertEqual(kinds['contradiction'], 1)
        self.assertEqual(kinds['consistent'], 11)
        stale = [m for m in ARTIFACT['transactions']['matches']
                 if m['classification'].startswith('stale')]
        self.assertEqual(stale[0]['player'], 'Daiyan Henley')
        self.assertEqual(stale[0]['club'], 'LAC')

    def test_reserve_list_names_that_the_report_does_not_carry(self):
        names = {e['player'] for e in ARTIFACT['transactions']['events_not_on_report']}
        self.assertIn('Malik Willis', names)      # injured reserve, not healthy
        self.assertIn('Jacoby Brissett', names)   # traded to BAL on 11/06

    def test_every_match_carries_an_official_player_link(self):
        for m in ARTIFACT['transactions']['matches']:
            self.assertTrue(m['player_url'].startswith('https://www.nfl.com/players/'), m)


class TestPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from build import render
        cls.pages = render()

    def test_page_is_generated_and_linked_from_the_navigation(self):
        html = self.pages['teams-availability.html']
        self.assertIn('Per-team availability view', html)
        self.assertIn('teams-availability.html', self.pages['index.html'])
        for heading in ['Re-count of every circulating Week 10 figure',
                        'Point-in-time position of the only retained availability capture',
                        'Roster-event conflicts: the report against the official transactions log',
                        'Announced-starter evidence, recorded as published (never inferred)',
                        'The injury signal as a change, not a level']:
            self.assertIn(heading, html)

    def test_no_depth_tier_is_invented_on_the_new_page(self):
        banned = ('1st string', '2nd string', '3rd string', '4th string',
                  'second string', 'third string', 'fourth string')
        html = self.pages['teams-availability.html']
        for word in banned:
            self.assertNotIn(word, html)

    def test_no_performance_or_profit_claim_appears(self):
        """The page counts rows on a report. It may not assert a market or performance conclusion.

        The site-wide disclaimer is excluded because it is a denial ("no verified edge"), and the
        navigation is excluded because it names other pages.
        """
        html = self.pages['teams-availability.html']
        body = html.split('<main', 1)[1].split('</main>')[0]
        body = re.sub(r'<p class="disclaimer">.*?</p>', '', body, flags=re.S)
        self.assertNotIn('ROI', body)
        for pattern in (r'\bwin rate\b', r'profitab', r'\bedge\b', r'\bcovers\b',
                        r'\bimplied probability\b', r'\bvalue bet\b'):
            self.assertIsNone(re.search(pattern, body, re.I), pattern)

    def test_flags_page_carries_the_seven_new_items(self):
        html = self.pages['flags.html']
        for i in range(1, 8):
            self.assertIn('AV-0%d' % i, html)
        self.assertIn('Flagged by the Week 10 availability re-count', html)

    def test_the_capture_is_cited_by_hash_not_by_adjective(self):
        html = self.pages['teams-availability.html']
        self.assertIn(ARTIFACT['capture']['sha256'][:16], html)
        self.assertIn(ARTIFACT['capture']['retrieved_at_utc'], html)


class TestFailClosedParsing(unittest.TestCase):
    def test_status_vocabulary_is_pinned(self):
        rows, _blocks = RECOUNT.parse_capture()
        allowed = {'', 'Out', 'Doubtful', 'Questionable'}
        self.assertTrue({r['game_status'] for r in rows} <= allowed)

    def test_transactions_and_byes_come_from_committed_official_transcriptions(self):
        self.assertEqual(ARTIFACT['bye_clubs'], ['CHI', 'DEN', 'PHI', 'TB'])
        self.assertEqual(sorted(ARTIFACT['depth_charts_in_repo']['clubs']), ['DET', 'KC', 'SEA'])
        self.assertIn('unofficial', ARTIFACT['depth_charts_in_repo']['status'].lower())


if __name__ == '__main__':
    unittest.main()
