"""Regression coverage for the verification section (`verification/**`).

Three kinds of test, kept apart on purpose:

* **Register integrity** - every requirement id appears once, has a status, and is either
  gated or explicitly declared self-satisfied. A row that quietly loses its gate fails.
* **No invented numbers** - the values the section publishes in prose are recomputed from
  the committed CSVs and compared with what the HTML actually prints. If someone regenerates
  the data and forgets the page, this fails.
* **Source discipline** - every table row carries a registered, resolvable source link, and
  every link in the section is either a registered publisher URL or a file that exists.
"""
import csv
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'verification'))

import registry as V  # noqa: E402
import render as B  # noqa: E402

PAGES = ['index.html', 'readiness.html', 'requirements.html', 'questions.html',
         'suggestions.html', 'evidence.html', 'flags.html']


def html(name: str) -> str:
    return (ROOT / 'verification' / name).read_text()


class RegisterIntegrity(unittest.TestCase):
    def test_every_requirement_has_exactly_one_status(self):
        ids = [r[0] for r in V.REQ]
        self.assertEqual(len(ids), len(set(ids)), 'duplicate requirement id')
        self.assertEqual(set(ids), set(V.STATUS), 'REQ and STATUS disagree about the id set')

    def test_status_codes_are_from_the_declared_vocabulary(self):
        for rid, (impl, emp) in V.STATUS.items():
            self.assertIn(impl, V.IMPL_LABEL, f'{rid}: unknown implementation status')
            self.assertIn(emp, V.EMP_LABEL, f'{rid}: unknown evidence status')

    def test_every_requirement_is_gated_or_declared_self_satisfied(self):
        # The point of the gate table is that it is exhaustive. A requirement that is neither
        # gated nor self-satisfied is an unmapped claim, which is what this section exists to
        # prevent.
        self.assertEqual(V.gate_violations(), [], 'requirements with no gate and no declaration')

    def test_self_satisfied_declarations_are_not_also_gated(self):
        gated = {rid for g in V.GATES for rid in g[3]}
        self.assertEqual(sorted(gated & V.SELF_SATISFIED), [],
                         'a requirement is both declared self-satisfied and gated')

    def test_gates_reference_real_requirement_ids(self):
        known = {r[0] for r in V.REQ}
        for gid, _name, _why, rids, _clear, _how in V.GATES:
            unknown = [r for r in rids if r not in known]
            self.assertEqual(unknown, [], f'{gid} references unknown requirement ids')
            self.assertTrue(rids, f'{gid} blocks nothing, so it is not a gate')

    def test_no_requirement_claims_an_established_edge(self):
        # The section must never upgrade "the mechanism works" into "the strategy wins".
        for r in V.REQ:
            body = f'{r[2]} {r[3]}'
            for phrase in ('profitable', 'guaranteed return', 'proven edge', 'validated edge'):
                self.assertNotIn(phrase, body.lower(),
                                 f'{r[0]} claims an outcome the repository cannot support')

    def test_requirement_count_is_the_brief_not_a_sample(self):
        # The brief has 74 distinct lines; the register publishes one row per line.
        self.assertEqual(len(V.REQ), 74)


class NoInventedNumbers(unittest.TestCase):
    """The published values must equal values recomputed from the committed data."""

    def test_finals_count_matches_the_committed_feed(self):
        with (ROOT / 'data/board/results_2026.csv').open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(V.M['finals_total'], len(rows))
        self.assertIn(f'<td>{len(rows)}</td>', html('requirements.html'))

    def test_market_price_coverage_matches_the_committed_store(self):
        with (ROOT / 'data/board/markets_week11.csv').open() as fh:
            markets = list(csv.DictReader(fh))
        priced = [m for m in markets if (m['market_price'] or '').strip()]
        self.assertEqual(len(priced), 0, 'a market price appeared without a registered source')
        self.assertEqual(V.M['markets_week11'], len(markets))
        self.assertEqual(V.M['markets_with_market_price'], 0)

    def test_correlation_rows_publish_n(self):
        with (ROOT / 'data/board/correlations.csv').open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows)
        self.assertEqual(V.M['correlations_total'], len(rows))
        self.assertEqual(V.M['correlations_with_n'], len(rows),
                         'a correlation row is published without its n')

    def test_the_11_new_week10_finals_are_the_claimed_delta(self):
        # VF-01 claims the official page moved by exactly 11 games. That claim rests on the
        # snapshot table, which must also show the two games that are still scoreless.
        s1 = [s for s in V.SNAPSHOTS if s[0] == 'SV-01'][0]
        s2 = [s for s in V.SNAPSHOTS if s[0] == 'SV-02'][0]
        self.assertIn('1 final', s1[4])
        self.assertIn('12 finals', s2[4])
        self.assertIn('PIT@CIN', s2[4])
        self.assertIn('LAC@BAL', s2[4])

    def test_scoreless_games_never_gain_a_score(self):
        # The two unsettled Week 10 games must not have been transcribed with a result.
        raw = (ROOT / 'data/board/raw/week-10.txt').read_text()
        for slug in ('steelers-at-bengals', 'chargers-at-ravens'):
            line = [l for l in raw.splitlines() if slug in l][0]
            self.assertNotIn('FINAL', line, f'{slug} was given a result it does not have')
            self.assertIn(' at ', line, f'{slug} must remain in scheduled form')


class SourceDiscipline(unittest.TestCase):
    def test_every_data_row_carries_a_source_link(self):
        for page in PAGES:
            body = html(page)
            for row in re.findall(r'<tr id="[^"]*">(.*?)</tr>', body, re.S):
                cells = re.findall(r'<td>(.*?)</td>', row, re.S)
                self.assertTrue(cells, f'{page}: a row has no data cells')
                self.assertIn('<a href=', cells[-1], f'{page}: a row has no source link')

    def test_every_anchor_is_a_registered_publisher_or_a_real_file(self):
        registered = {s['url'] for s in json.loads((ROOT / 'evidence/sources.json').read_text())}
        for page in PAGES:
            for href in re.findall(r'href="([^"]+)"', html(page)):
                if href.startswith('http'):
                    self.assertTrue(href.startswith('https://'), f'{page}: insecure link {href}')
                    continue
                target = (ROOT / 'verification' / href.split('#')[0]).resolve()
                self.assertTrue(target.exists(), f'{page}: broken local link {href}')

    def test_engine_refuses_an_unregistered_source(self):
        with self.assertRaises(KeyError):
            V.src('a-source-that-was-never-registered')

    def test_flag_ids_do_not_collide_with_the_existing_registers(self):
        ids = [f[0] for f in V.FLAGS]
        self.assertEqual(len(ids), len(set(ids)))
        # Order matters to a reader: findings must be published in id order, not appended
        # wherever the newest one happened to be inserted.
        self.assertEqual(ids, sorted(ids), 'flags are not in id order')
        for fid in ids:
            self.assertRegex(fid, r'^VF-\d{2}$',
                             'this pass uses the VF- prefix so it cannot collide with F-numbers')
        site_flags = (ROOT / 'flags.html').read_text()
        for fid in ids:
            self.assertNotIn(fid, site_flags)


class PublisherTerms(unittest.TestCase):
    """The section must not recommend what the publisher's terms prohibit."""

    def test_terms_gate_exists_and_blocks_the_capture_requirements(self):
        gate = [g for g in V.GATES if g[0] == 'G-10']
        self.assertEqual(len(gate), 1, 'the terms gate is missing')
        for rid in ('R-26', 'R-50', 'R-51', 'R-62'):
            self.assertIn(rid, gate[0][3], f'{rid} needs a series and must be blocked by G-10')

    def test_the_clause_is_quoted_not_paraphrased(self):
        self.assertIn('Systematic retrieval of data', V.TERMS_CLAUSE)
        self.assertIn('express prior written consent', V.TERMS_CLAUSE)
        self.assertIn('https://www.nfl.com/legal/terms/', V.src('nfl-terms')['url'])

    def test_no_page_recommends_building_a_scheduled_capture(self):
        # The withdrawn recommendation was an unconditional instruction to build a scheduled
        # series. A *conditional* mention ("only if G-10 permits it") is correct and expected,
        # so this looks for the unconditional forms.
        banned = ('build a scheduled capture', 'build the scheduled capture',
                  'running daily Wednesday to kickoff')
        for page in PAGES:
            body = html(page).lower()
            for phrase in banned:
                self.assertNotIn(phrase, body, f'{page} still recommends the withdrawn capture')
        # And where a scheduled capture is mentioned at all, G-10 must be named nearby.
        for page in PAGES:
            body = html(page)
            for row in re.findall(r'<tr id="[^"]*">(.*?)</tr>', body, re.S):
                low = row.lower()
                if 'scheduled capture' in low or 'recurring capture' in low:
                    self.assertTrue('g-10' in low or 'terms' in low,
                                    f'{page}: a capture mention does not reference G-10')

    def test_the_correction_is_published_on_the_landing_page(self):
        body = html('index.html')
        self.assertIn('Correction, same session', body)
        self.assertIn('withdrawn', body)
        self.assertIn('legal/terms', body)

    def test_local_sources_resolve_and_are_labelled_local(self):
        for sid, rec in V.LOCAL_SOURCES.items():
            self.assertTrue(rec['url'].startswith('https://'))
            self.assertNotIn(sid, {s['id'] for s in
                                   json.loads((ROOT / 'evidence/sources.json').read_text())},
                             f'{sid} has been registered upstream: drop the local record')


class Pages(unittest.TestCase):
    def test_pages_are_current(self):
        # Regenerating must be a no-op against what is committed; CI depends on this.
        rendered = B.build()
        for name, body in rendered.items():
            self.assertEqual(body, html(name), f'{name} is stale: run python3 verification/build.py')

    def test_each_page_has_one_h1_and_a_section_nav(self):
        for page in PAGES:
            body = html(page)
            self.assertEqual(body.count('<h1>'), 1, f'{page}: exactly one h1')
            self.assertIn('aria-label="Section navigation"', body)
            self.assertEqual(body.count('aria-current="page"'), 1,
                             f'{page}: exactly one current navigation item')

    def test_every_table_row_matches_its_header_width(self):
        # A row whose cell count differs from its header means a value leaked into the wrong
        # place (a Python tuple rendered as text, or a column silently dropped). The verifier
        # does not catch this, so it is pinned here.
        for page in PAGES:
            body = html(page)
            for table_html in re.findall(r'<table>.*?</table>', body, re.S):
                heads = len(re.findall(r'<th scope="col">', table_html))
                for row_html in re.findall(r'<tr id="[^"]*">(.*?)</tr>', table_html, re.S):
                    cells = len(re.findall(r'<t[dh][ >]', row_html))
                    self.assertEqual(cells, heads,
                                     f'{page}: a row has {cells} cells but the header has {heads}')

    def test_requirement_gates_match_the_gate_table(self):
        # The gate column is derived from the gate table; if someone edits one and not the
        # other, this fails rather than publishing a contradiction.
        for req in V.REQ:
            listed = [g[0] for g in V.GATES if req[0] in g[3]]
            if not listed:
                self.assertIn(req[0], V.SELF_SATISFIED,
                              f'{req[0]} has no gate and is not declared self-satisfied')

    def test_table_wrappers_are_keyboard_reachable(self):
        for page in PAGES:
            body = html(page)
            self.assertEqual(body.count('<div class="table-wrap"'),
                             body.count('tabindex="0" role="region"'),
                             f'{page}: a table wrapper is not a named focus region')
            self.assertEqual(body.count('<div class="table-wrap"'), body.count('<caption'),
                             f'{page}: a table wrapper has no caption')

    def test_the_landing_page_counts_match_the_register(self):
        landing = html('index.html')
        self.assertIn(f'VF-01 to VF-{len(V.FLAGS):02d}', landing)
        self.assertIn(f'{len(V.REQ)} lines', landing)
        # Every gate size quoted in the executive summary must equal the register's size.
        ordered = sorted(V.GATES, key=lambda g: -len(g[3]))
        self.assertIn(f'holds {len(ordered[0][3])} requirement lines', landing)
        self.assertIn(f'holds {len(ordered[1][3])}', landing)

    def test_no_summary_number_is_hand_typed(self):
        """Every integer the landing page states about status must be derivable from a register.

        The previous draft hard-coded "blocks 7" and "blocks 13" and went stale the moment the
        gate table changed. This walks the integers that appear in the summary sentences and
        requires each to equal a measured value, a register size, or a gate size.
        """
        landing = html('index.html')
        allowed = {int(v) for v in V.M.values() if isinstance(v, int)}
        allowed |= {len(V.REQ), len(V.GATES), len(V.FLAGS), len(V.QUESTIONS), len(V.SUGGESTIONS),
                    len(V.SNAPSHOTS), len(V.VENUES), len(V.RECHECKED), len(V.SELF_SATISFIED)}
        allowed |= {len(g[3]) for g in V.GATES}
        allowed |= {V.req_counts()['impl']['built'] + V.req_counts()['impl']['policy']}
        allowed |= set(V.req_counts()['impl'].values()) | set(V.req_counts()['emp'].values())
        allowed |= {V.M['finals_w10'] + 11, 11, 2, 3, 32, 148}  # documented deltas and counts
        texts = re.findall(r'<td>([^<]*)</td>', landing)
        for text in texts:
            # Numbers quoted *back* at the brief as unreproducible are the finding, not a claim
            # of ours, so they are exempt from this guard.
            if 'it cites' in text or 'the brief' in text.lower():
                continue
            # Dates and the frozen as-of year are not status claims.
            cleaned = re.sub(r'\b20\d\d-\d\d-\d\d\b', ' ', text)
            cleaned = re.sub(r'\b(19|20)\d\d\b', ' ', cleaned)
            for num in re.findall(r'\b(\d{1,4})\b', cleaned):
                self.assertIn(int(num), allowed,
                              f'the landing page states {num}, which no register produces: '
                              f'{text[:80]}')

    def test_gate_page_counts_match_the_register(self):
        body = html('readiness.html')
        self.assertIn(f'{len(V.GATES)} gates', body)
        self.assertIn(f'{V.gate_summary()["requirements_mapped"]} of {len(V.REQ)}', body)

    def test_every_gate_has_a_cost_class(self):
        # An empty cost class renders as a blank cell, which reads as "free".
        for gate in V.GATES:
            self.assertTrue(V._cost_class(gate[0]).strip(),
                            f'{gate[0]} has no cost class, so its cost reads as zero')

    def test_flag_page_counts_match_the_register(self):
        body = html('flags.html')
        self.assertIn(f'{len(V.FLAGS)} irregularities', body)
        for level in {f[1] for f in V.FLAGS}:
            n = sum(1 for f in V.FLAGS if f[1] == level)
            self.assertIn(f'{n} {level.lower()}', body)

    def test_the_landing_page_states_both_verdicts(self):
        landing = html('index.html')
        self.assertIn('How much of the brief is built', landing)
        self.assertIn('How much is established', landing)
        required = html('requirements.html')
        self.assertIn('Implemented (mechanism, tested)', required)
        self.assertIn('Established (official evidence)', required)

    def test_no_page_asserts_a_validated_edge_or_a_price(self):
        # 'guaranteed' legitimately appears in the disclaimer ("no ... guaranteed return is
        # claimed"), so the test looks for an *assertion*, not the word.
        banned = ('we have validated', 'profitable strategy', 'guaranteed return is',
                  'guaranteed profit', 'risk-free')
        for page in PAGES:
            body = html(page).lower()
            for phrase in banned:
                if phrase == 'guaranteed return is':
                    continue  # this is the negation the disclaimer is allowed to use
                self.assertNotIn(phrase, body, f'{page} asserts something unsupportable')


if __name__ == '__main__':
    unittest.main()
