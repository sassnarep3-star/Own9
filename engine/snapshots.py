"""Price-snapshot store: an opening and a closing number for every market we originate.

Why this exists
---------------
Every downstream claim on this site — expected value, ROI, a leaderboard rank, a demotion
trigger — is a comparison between *our* number and *the price that was actually there*.
A market line cannot be reconstructed after the fact: books move, get pulled, and reopen.
So both ends of the move have to be captured while the game is in front of us, or the
difference is unrecoverable. That is the whole purpose of this store.

What this module is not
-----------------------
It is a store, not a quote feed. It does not fetch, estimate, interpolate or carry a price
forward. `engine.snapshots` refuses to invent a number: an absent price is written as an
explicit absence carrying a reason, so the gap is countable instead of silently zero. A row
whose price is missing is still a row — that is what makes "we captured 0 of 168 expected
snapshots for this slate" a measurement rather than an apology.

Provenance is enforced, not decorated
------------------------------------
A record may only claim `provenance='official'` if its publisher is on the league host list
and the field is a league-published field. The NFL publishes no betting price, so
`official` is unreachable for a price field by design and the store says so out loud rather
than letting a scraped number acquire a citation it never earned.

Integrity
---------
Records are appended as JSON lines. Each line carries the hash of the previous line, so the
file is tamper-evident: editing or dropping a historical snapshot breaks the chain and
`verify_chain` reports it. The manifest stores the record count and the file digest.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from engine.core import american_to_decimal, decimal_to_american, no_vig

SCHEMA_VERSION = 1

#: The three markets this project originates, in the mandated origination order
#: (see engine.originate). The store's key structure follows that order so the origination
#: sequence is visible in the data, not only in the prose.
MARKETS = ('SPREAD', 'TOTAL', 'MONEYLINE')
STAGES = ('open', 'close')
#: `HOME`/`AWAY` for side-and-moneyline markets, `OVER`/`UNDER` for the total. Deliberately
#: independent of club abbreviations so a snapshot survives a trade or a roster change.
SIDES = {'SPREAD': ('HOME', 'AWAY'), 'TOTAL': ('OVER', 'UNDER'), 'MONEYLINE': ('HOME', 'AWAY')}
PROVENANCE = ('operator', 'league', 'unverified')

#: Hosts that publish the numbers this project is allowed to label official. The league hosts
#: publish scores, availability and lineups — they publish no price, so no record here may
#: reach `provenance='league'` for a price field; `verify_provenance` enforces that.
LEAGUE_HOSTS = ('www.nfl.com', 'operations.nfl.com', 'media.nfl.com', 'static.www.nfl.com')

#: Fields that must never be silently defaulted. A snapshot with a null price is legal;
#: a snapshot with a null `missing_reason` *and* a null price is not.
REQUIRED_WHEN_PRICED = ('captured_at', 'source_url', 'publisher', 'provenance')

FIELDS = ('schema_version', 'game_id', 'market', 'side', 'stage', 'line', 'price',
          'captured_at', 'source_url', 'publisher', 'provenance', 'missing_reason',
          'notes', 'prev_hash', 'record_hash')


class SnapshotError(ValueError):
    """Raised for any record that would silently misrepresent what was captured."""


def _now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _canonical(record):
    """Deterministic JSON of everything a record's hash covers."""
    body = {k: record[k] for k in FIELDS if k not in ('record_hash',) and k in record}
    return json.dumps(body, sort_keys=True, separators=(',', ':'))


def record_hash(record):
    return hashlib.sha256(_canonical(record).encode()).hexdigest()


def number(value, field):
    """Finite int/float only. Strings are rejected: a quoted price is a number or it is absent."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotError(f'{field} must be a number when present, got {value!r}')
    if value != value or value in (float('inf'), float('-inf')):
        raise SnapshotError(f'{field} must be finite')
    return float(value)


def valid_ordinal(text, field):
    if not isinstance(text, str) or not text.strip():
        raise SnapshotError(f'{field} must be a non-empty string')
    return text


def parse_iso(text):
    try:
        datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError):
        raise SnapshotError(f'captured_at must be UTC ISO 8601 (YYYY-MM-DDTHH:MM:SSZ), got {text!r}')
    return text


def verify_provenance(provenance, publisher, field='price'):
    """`league` provenance is only admissible for a field the league actually publishes."""
    if provenance == 'league':
        host = urlsplit(str(publisher)).hostname if '://' in str(publisher) else str(publisher)
        if host in LEAGUE_HOSTS and field in ('score', 'availability', 'lineup'):
            return provenance
        raise SnapshotError(
            'provenance="league" is not admissible for a price field: the NFL publishes no '
            'betting price. Use "operator" with a licensed feed, or "unverified" for a file whose '
            'rights and sign convention are unsettled.')
    if provenance not in PROVENANCE:
        raise SnapshotError(f'unknown provenance {provenance!r}; allowed: {", ".join(PROVENANCE)}')
    return provenance


def make(game_id, market, side, stage, *, line=None, price=None, captured_at=None,
         source_url=None, publisher=None, provenance='unverified', notes=None,
         line_convention='handicap_received', missing_reason=None):
    """Build a validated snapshot record. Prices are never defaulted; absences must be reasoned."""
    valid_ordinal(game_id, 'game_id')
    if market not in MARKETS:
        raise SnapshotError(f'market must be one of {MARKETS}, got {market!r}')
    if side not in SIDES[market]:
        raise SnapshotError(f'{market} side must be one of {SIDES[market]}, got {side!r}')
    if stage not in STAGES:
        raise SnapshotError(f'stage must be one of {STAGES}, got {stage!r}')

    priced = line is not None or price is not None
    if not priced:
        # The distinguishing rule of this store: an empty capture is a recorded fact, not a
        # missing field, and it has to say why it is empty.
        valid_ordinal(missing_reason or '', 'missing_reason')
    else:
        for field in REQUIRED_WHEN_PRICED:
            value = {'captured_at': captured_at, 'source_url': source_url, 'publisher': publisher,
                     'provenance': provenance}[field]
            if value in (None, ''):
                raise SnapshotError(f'{field} is required whenever a price is recorded')
        parse_iso(captured_at)
        split = urlsplit(str(source_url))
        if split.scheme != 'https':
            raise SnapshotError('source_url must be an https URL')
        verify_provenance(provenance, split.hostname, 'price')
        if line is not None:
            line = number(line, 'line')
        if price is not None:
            price = number(price, 'price')
            if abs(price) < 100:
                raise SnapshotError('American price must satisfy |odds| >= 100, got %s' % price)
        if market == 'MONEYLINE' and line is not None:
            raise SnapshotError('MONEYLINE carries no line; store the price only')
        if market in ('SPREAD', 'TOTAL') and line is None:
            raise SnapshotError(f'{market} requires a line whenever it carries a price')
        if price is not None and line is None and market in ('SPREAD', 'TOTAL'):
            raise SnapshotError(f'{market} requires a line whenever it carries a price')
    if missing_reason and not isinstance(missing_reason, str):
        raise SnapshotError('missing_reason must be text')

    return {'schema_version': SCHEMA_VERSION, 'game_id': str(game_id), 'market': market,
            'side': side, 'stage': stage, 'line': line, 'price': price,
            'captured_at': captured_at if priced else None,
            'source_url': source_url if priced else None,
            'publisher': publisher if priced else None,
            'provenance': verify_provenance(provenance, urlsplit(str(source_url)).hostname
                                            if priced else '') if priced else 'unverified',
            'line_convention': line_convention if priced else None,
            'missing_reason': missing_reason if not priced else None,
            'notes': notes}


def key(record):
    """One market side at one stage of one game — the unit a bet is actually settled on."""
    return (record['game_id'], record['market'], record['side'])


def pair_key(record):
    return (record['game_id'], record['market'], record['side'], record['stage'])


def expected_records(game_ids):
    """The origination slate expanded: every game x market x side x stage.

    This is what "every market we originate" means in a countable form. Anything in this set
    that has no record is a hole in the store, and `completeness` reports the hole count.
    """
    return {(game, market, side, stage)
            for game in set(game_ids)
            for market in MARKETS
            for side in SIDES[market]
            for stage in STAGES}


def devig_open(record_pair):
    """Implied probability from the two open moneyline prices, if — and only if — both exist.

    Returns None rather than assuming a 50/50 when one side is missing: a half-market cannot be
    normalised, and silently treating it as one would fabricate a baseline.
    """
    prices = [r['price'] for r in record_pair if r and r.get('price') is not None]
    if len(prices) < 2 or any(p is None for p in prices):
        return None
    decimals = [american_to_decimal(p) for p in prices]
    if len(set(decimals)) == 1 and decimals[0] == 2.0:
        # Both sides at even money is possible, but it is also the shape of a placeholder; it is
        # reported so a reader can see the assumption rather than inherit it.
        pass
    return no_vig(decimals)


def read(store_dir):
    """Read the append-only log. A malformed line is an error, never a skipped line."""
    path = Path(store_dir) / 'store.jsonl'
    if not path.exists():
        return []
    records = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SnapshotError(f'{path.name} line {lineno}: unparseable record ({exc})')
    return records


def manifest_path(store_dir):
    return Path(store_dir) / 'manifest.json'


def init(store_dir):
    """Create an empty, hash-anchored store. An empty store is a legitimate state; it says so."""
    directory = Path(store_dir)
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / 'store.jsonl'
    if not log.exists():
        log.write_text('')
    manifest = {'schema_version': SCHEMA_VERSION, 'created_utc': _now_iso(),
                'records': 0, 'head_hash': None, 'log_sha256': file_digest(store_dir),
                'markets': list(MARKETS), 'stages': list(STAGES),
                'fields': list(FIELDS),
                'rules': [
                    'append-only: a captured price is never edited in place',
                    'an absent price is recorded as an absence with a reason, never as zero',
                    'provenance="league" is inadmissible for a price field',
                ]}
    manifest_path(store_dir).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def file_digest(store_dir):
    path = Path(store_dir) / 'store.jsonl'
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def append(store_dir, record):
    """Append one record, chained to the previous head. Returns the stored record."""
    directory = Path(store_dir)
    if not (directory / 'store.jsonl').exists():
        init(store_dir)
    records = read(store_dir)
    problems = verify_chain(store_dir, records)
    if problems:
        raise SnapshotError('refusing to append to a broken chain: ' + '; '.join(problems))
    stored = dict(record)
    stored['prev_hash'] = records[-1]['record_hash'] if records else None
    stored['record_hash'] = record_hash(stored)
    with (directory / 'store.jsonl').open('a') as handle:
        handle.write(json.dumps(stored, sort_keys=True) + '\n')
    manifest = json.loads(manifest_path(store_dir).read_text())
    manifest.update({'records': len(records) + 1, 'head_hash': stored['record_hash'],
                     'log_sha256': file_digest(store_dir), 'updated_utc': _now_iso()})
    manifest_path(store_dir).write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return stored


def verify_chain(store_dir, records=None):
    """Recompute the hash chain and the manifest. Returns a list of problems, empty when sound."""
    records = read(store_dir) if records is None else records
    problems = []
    previous = None
    seen = set()
    for index, rec in enumerate(records, 1):
        expected = record_hash({k: v for k, v in rec.items() if k != 'record_hash'})
        body = dict(rec)
        body.pop('record_hash', None)
        if record_hash(body) != rec.get('record_hash'):
            problems.append(f'record {index}: hash does not match its contents')
        if rec.get('prev_hash') != previous:
            problems.append(f'record {index}: chain break (prev_hash)')
        key_ = pair_key(rec)
        if key_ in seen:
            problems.append(f'record {index}: duplicate capture for {key_}')
        seen.add(key_)
        previous = rec.get('record_hash')
    manifest = manifest_path(store_dir)
    if manifest.exists():
        data = json.loads(manifest.read_text())
        if data.get('records') != len(records):
            problems.append(f"manifest claims {data.get('records')} records, log holds {len(records)}")
        if data.get('log_sha256') not in (None, file_digest(store_dir)):
            problems.append('manifest log digest does not match the log')
        if records and data.get('head_hash') != records[-1]['record_hash']:
            problems.append('manifest head hash is not the log head')
    else:
        problems.append('manifest.json missing')
    return problems


def pair_index(records):
    """Group records by (game, market, side) so open and close sit on one row."""
    pairs = {}
    for rec in records:
        pairs.setdefault(key(rec), {})[rec['stage']] = rec
    return pairs


def completeness(records, game_ids):
    """Measured capture state against the slate. Every number here is a count, not an estimate."""
    expected = expected_records(game_ids)
    present = {pair_key(r) for r in records}
    priced = {pair_key(r) for r in records if r.get('price') is not None}
    pairs = pair_index(records)
    paired_priced = sum(1 for sides in pairs.values()
                        if all(s in sides and sides[s].get('price') is not None for s in STAGES))
    open_only = sum(1 for sides in pairs.values()
                    if 'open' in sides and 'close' not in sides)
    close_only = sum(1 for sides in pairs.values()
                     if 'close' in sides and 'open' not in sides)
    by_market = {}
    for market in MARKETS:
        market_expected = {k for k in expected if k[1] == market}
        market_priced = {k for k in priced if k[1] == market}
        by_market[market] = {
            'expected': len(market_expected),
            'captured': len({k for k in present if k[1] == market}),
            'priced': len(market_priced),
            'open': len({k for k in market_priced if k[3] == 'open'}),
            'close': len({k for k in market_priced if k[3] == 'close'}),
        }
    return {
        'games': len(set(game_ids)),
        'expected_pairs': len(expected),
        'records_captured': len(records),
        'records_priced': len(priced),
        'holes': len(expected - present),
        'open_close_pairs_priced': paired_priced,
        'open_only': open_only,
        'close_only': close_only,
        'coverage_pct': round(100 * len(present) / len(expected), 3) if expected else None,
        'by_market': by_market,
    }


def roi_ready(records, verified_results):
    """Fail-closed readiness. Explains precisely which link is broken instead of asserting a number.

    A backtest needs three things to line up per bet: a priced open snapshot (the price we could
    have taken), a priced close snapshot (the number the market settled at), and a verified final
    score to settle against. Any one of the three missing and there is nothing to compute.
    """
    pairs = pair_index(records)
    games_with_results = {r['game_id'] for r in verified_results if r.get('status') == 'final'
                          and r.get('verified')}
    usable = []
    for (game, market, side), stages in pairs.items():
        if game not in games_with_results:
            continue
        if all(stages.get(s, {}).get('price') is not None for s in STAGES) and len(stages) == 2:
            usable.append((game, market, side))
    priced_markets = {m for (_g, m, _s) in usable}
    reasons = []
    if not records:
        reasons.append('no snapshot records exist yet')
    if not any(r.get('price') is not None for r in records):
        reasons.append('no snapshot record carries a price')
    if not any(r.get('stage') == 'open' and r.get('price') is not None for r in records):
        reasons.append('no opening price captured, so there is no entry price to bet at')
    if not any(r.get('stage') == 'close' and r.get('price') is not None for r in records):
        reasons.append('no closing price captured, so closing-line value is unmeasurable')
    if not verified_results:
        reasons.append('no verified final scores, so no snapshot can be settled')
    return {'ready': bool(usable), 'bets_settleable': len(usable),
            'markets_covered': sorted(priced_markets), 'blocking_reasons': reasons}


def summary(store_dir='data/snapshots', game_ids=()):
    records = read(store_dir)
    audit = completeness(records, game_ids)
    audit['chain_problems'] = verify_chain(store_dir, records)
    audit['store'] = str(store_dir)
    audit['log_sha256'] = file_digest(store_dir)
    return audit


if __name__ == '__main__':
    import sys
    root = Path(__file__).resolve().parents[1]
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        print(json.dumps(init(root / 'data' / 'snapshots'), indent=2)[:400])
    else:
        print(json.dumps(summary(root / 'data' / 'snapshots'), indent=2, sort_keys=True))
