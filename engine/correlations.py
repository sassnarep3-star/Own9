"""Correlations from official numbers only, with `n` printed beside every value.

The two failure modes this closes
---------------------------------
1. *Mixed provenance.* A correlation computed from one officially sourced leg and one scraped,
   undocumented or model-generated leg is not a measurement of anything; it is a summary of two
   different epistemic categories. So every observation must carry a source id, and any id outside
   the registered official set fails the whole pair. Not the row — the pair, because a partially
   unverified correlation is still an unverified correlation.
2. *A number without a denominator.* `r = 0.42` on its own is the most misleading format in this
   field: it reads the same whether it came from fifteen games or fifteen hundred. Every published
   value here is a tuple of estimate, `n`, interval and verdict, and `measure` refuses to return
   one without the other three.

Predeclared decision constants
------------------------------
`MIN_N` and `DEADBAND` below are declared before any measurement was run in this module, and they
are the values used for every published verdict. They are not tuned to a result. `MIN_N` is the
smallest number of aligned paired games this project will act on; `DEADBAND` is the smallest
absolute correlation it will act on at all. Anything short of both leaves a joint price blank
rather than assuming independence — the asymmetry is deliberate, since assuming independence is a
bet, not a default.

Test inputs
-----------
The synthetic fixtures in `tests/` exist to prove the gate behaves; they are arithmetic on made-up
numbers and are never NFL claims.
"""
from engine.core import (correlation_interval, dependence_gate, joint_price_from_dependence,
                         pearson)
from pathlib import Path

from engine.snapshots import SnapshotError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'evidence' / 'sources.json'

#: Host classes. A score or statistics input may only come from the league; an availability or
#: depth input may also come from a club, because that is where depth is published at all. Keeping
#: the two classes separate is what stops a self-labelled unofficial club page being treated as an
#: authoritative source for a game result.
LEAGUE_ONLY_HOSTS = frozenset({'www.nfl.com', 'operations.nfl.com', 'media.nfl.com',
                               'static.www.nfl.com'})
CLUB_ALLOWED_HOSTS = frozenset({'www.chiefs.com', 'www.seahawks.com', 'www.detroitlions.com',
                                'www.patriots.com'})
FIELD_CLASSES = ('score', 'availability', 'statistics')

#: Registered official sources whose numbers may enter a correlation. Anything else fails closed.
#: This allowlist is checked *in addition to* the manifest lookup in `resolve_sources`, so an id
#: must be both declared here and actually registered as an official publisher record.
OFFICIAL_SOURCES = frozenset({
    'nfl-schedule-w8-byweek', 'nfl-schedule-w9', 'nfl-schedule-w10', 'nfl-schedule-w10-byweek', 'nfl-gamebook-w10',
    'nfl-gamebook-w9-lar-was', 'nfl-gamebook-w9-nyg-phi', 'nfl-injury', 'nfl-injury-w10',
    'nfl-stats', 'nfl-player-stats', 'nfl-stats-cats', 'nfl-roster', 'nfl-roster-status',
    'nfl-transactions', 'nfl-reserve-list', 'nfl-gamecenter-w10', 'nfl-gamecenter-score',
    'chiefs-depth', 'seahawks-depth', 'seahawks-depth-1cf', 'lions-depth', 'club-depth-chart',
})
#: Paired game observations required before a verdict may influence a decision.
MIN_N = 30
#: Smallest |r| the project will act on, predeclared.
DEADBAND = 0.10
#: Confidence level for the published interval.
CONFIDENCE = 0.95


class CorrelationGate(SnapshotError):
    """Raised when a pair would be computed from something other than official numbers."""


def resolve_sources(source_ids, *, field_class='score', allow_extra_sources=()):
    """Check each id against the evidence manifest, not just against this module's allowlist.

    A source id is admitted when it is (a) in `OFFICIAL_SOURCES`, (b) registered in
    `evidence/sources.json` with an https URL, and (c) published by a host whose class suits the
    field being measured. The manifest is the repository's record of pages actually read, so this
    makes "officially sourced" mean *registered as read from an official publisher*, not *named in a
    string somewhere*.
    """
    import json
    from urllib.parse import urlsplit
    allowed_hosts = set(LEAGUE_ONLY_HOSTS)
    if field_class == 'availability':
        allowed_hosts |= CLUB_ALLOWED_HOSTS
    manifest = {}
    if MANIFEST.exists():
        manifest = {entry['id']: entry for entry in json.loads(MANIFEST.read_text())}
    problems, resolved = [], []
    for source in sorted(set(source_ids)):
        if source not in (set(OFFICIAL_SOURCES) | set(allow_extra_sources)):
            problems.append(f'{source}: not in the official allowlist')
            continue
        entry = manifest.get(source)
        if entry is None:
            problems.append(f'{source}: not registered in evidence/sources.json')
            continue
        if entry.get('status') not in ('retrieved', 'inspected'):
            problems.append(f'{source}: manifest status {entry.get("status")!r} is not a read record')
            continue
        host = urlsplit(str(entry.get('url', ''))).hostname
        if host not in allowed_hosts:
            problems.append(f'{source}: host {host!r} is not an official publisher for a '
                            f'{field_class} field')
            continue
        resolved.append({'id': source, 'url': entry['url'], 'publisher': entry.get('publisher'),
                         'checked': entry.get('checked')})
    if problems:
        raise CorrelationGate('correlation refused; source resolution failed: ' + '; '.join(problems))
    return resolved


def require_official(pairs, *, allow_extra_sources=(), field_class='score'):
    """Every observation must name its source, and every source must resolve to an official record.

    Returns the sorted source set on success. Raises with the full list of offenders, because
    reporting only the first one invites a fix-then-rerun loop instead of a real repair.
    """
    named = sorted({source for pair in pairs for source in (pair.get('sources') or [])})
    allowed = set(OFFICIAL_SOURCES) | set(allow_extra_sources)
    missing = [index for index, pair in enumerate(pairs, 1) if not pair.get('sources')]
    unlisted = [f'observation {index}: {source}' for index, pair in enumerate(pairs, 1)
                for source in (pair.get('sources') or []) if source not in allowed]
    if missing or unlisted:
        raise CorrelationGate(
            'correlation refused; inputs are not all officially sourced'
            + (f' | unnamed source on observations: {missing}' if missing else '')
            + (f' | unregistered sources: {"; ".join(unlisted)}' if unlisted else ''))
    # The manifest check runs last so the caller sees the complete picture in one failure, and any
    # error it raises names the specific source that is not an official read record.
    resolve_sources(named, field_class=field_class, allow_extra_sources=allow_extra_sources)
    return named


def require_alignment(pairs):
    """Both legs must come from the same game, and a game may appear once per pair-set.

    A correlation across mismatched game ids is a statistic about two different populations.
    """
    problems, seen = [], {}
    for index, pair in enumerate(pairs, 1):
        game = pair.get('game_id')
        if not game:
            problems.append(f'observation {index}: no game id, so the legs cannot be shown to be '
                            'from the same game')
            continue
        legs = pair.get('leg_games')
        if legs and len(set(legs)) != 1:
            problems.append(f'observation {index}: legs come from different games {sorted(set(legs))}')
        if game in seen:
            problems.append(f'observation {index}: game {game} already used at observation {seen[game]}')
        seen[game] = index
    if problems:
        raise CorrelationGate('correlation refused; alignment failed: ' + '; '.join(problems))
    return len(seen)


def measure(label, pairs, *, fields=('a', 'b'), min_n=MIN_N, deadband=DEADBAND,
            confidence=CONFIDENCE, allow_extra_sources=(), level='game', field_class='score'):
    """One published row: estimate, n, interval, verdict, sources, and what it may be used for.

    `n` is taken from the observations actually used, never passed in by hand — a hand-typed
    denominator is how a stale `n` survives a data refresh.
    """
    sources = require_official(pairs, allow_extra_sources=allow_extra_sources,
                               field_class=field_class)
    aligned_games = require_alignment(pairs)
    xs, ys, used = [], [], []
    dropped = []
    for pair in pairs:
        a, b = pair.get(fields[0]), pair.get(fields[1])
        if a is None or b is None:
            dropped.append(pair.get('game_id'))
            continue
        xs.append(a)
        ys.append(b)
        used.append(pair.get('game_id'))
    n = len(used)
    row = {'label': label, 'level': level, 'n': n, 'aligned_games': aligned_games,
           'dropped_incomplete': len(dropped), 'sources': sources,
           'min_n': min_n, 'deadband': deadband, 'confidence': confidence,
           'inputs': f'{fields[0]} <-> {fields[1]}'}
    if n < 2:
        row.update({'r': None, 'interval': None, 'verdict': 'insufficient_evidence',
                    'may_price_joint': False,
                    'note': 'fewer than two complete pairs: no estimate exists', 'status': 'blank'})
        return row
    r = pearson(xs, ys)
    row['r'] = None if r is None else round(r, 6)
    interval = None if r is None else correlation_interval(r, n, confidence)
    row['interval'] = None if interval is None else [round(v, 6) for v in interval]
    if r is not None and interval is None:
        # |r| = 1 has no Fisher-z image, and a small n can also refuse. The estimate is still
        # reportable with its n; only the interval is unavailable, and that is stated.
        row['interval_note'] = ('no Fisher-z interval exists at |r| = 1, or n is too small to '
                               'form one')
    if r is None:
        # A constant leg makes the correlation undefined, not zero. Publishing 0.0 here would
        # report "no relationship" when the truth is "this pair has no variance to relate".
        row.update({'verdict': 'undefined_constant_leg', 'may_price_joint': False,
                    'note': 'one leg is constant across the sample, so r is undefined',
                    'status': 'undefined'})
        return row
    gate = dependence_gate(r, n, min_n, confidence=confidence, deadband=deadband)
    row.update({'verdict': gate['verdict'], 'may_price_joint': gate['may_price_joint'],
                'note': gate['reason'], 'status': 'measured',
                'gate_deadband': gate.get('deadband'), 'gate_interval':
                [round(v, 6) for v in gate['interval']] if gate.get('interval') else None})
    return row


def joint_probability(row, p_a, p_b):
    """The only route from a correlation to a price, and it is closed by default.

    Returns None whenever the verdict is not directional, which is how a joint price stays blank
    instead of silently falling back to the product of the marginals.
    """
    gate = {'verdict': row.get('verdict'), 'rho': row.get('r'),
            'may_price_joint': row.get('may_price_joint', False)}
    value = joint_price_from_dependence(p_a, p_b, gate)
    if value is None:
        return None
    return value


def value_rules():
    """The published discipline, as rows for the register page."""
    return [
        ('Sources', 'Every observation names a registered official source. One unregistered leg '
         'voids the whole pair, not just that row.'),
        ('Alignment', 'Both legs must come from the same game, and each game enters a pair-set '
         'once. Cross-game row mixing is rejected.'),
        ('Denominator', 'n is counted from the complete pairs actually used, never typed. n is '
         'printed with every value, including values that are refused.'),
        ('Missing legs', 'An observation missing either leg is dropped and counted. It is not '
         'imputed, and it does not shrink the denominator silently.'),
        ('Constant leg', 'Undefined, reported as undefined. Never replaced by 0.0.'),
        ('Action', 'A value may change a joint price only when the interval clears both the '
         f'MIN_N ({MIN_N}) and the deadband ({DEADBAND}), predeclared before measurement.'),
    ]


if __name__ == '__main__':  # pragma: no cover
    import json
    good = [{'game_id': f'g{i}', 'sources': ['nfl-schedule-w9'], 'a': i, 'b': i * 2 + 1}
            for i in range(35)]
    print(json.dumps(measure('synthetic demo pair (not an NFL claim)', good), indent=2))
    try:
        measure('bad', [{'game_id': 'g1', 'sources': ['some-blog'], 'a': 1, 'b': 2},
                        {'game_id': 'g2', 'sources': ['some-blog'], 'a': 2, 'b': 3}])
    except CorrelationGate as exc:
        print('\nrefused as designed:', exc)
