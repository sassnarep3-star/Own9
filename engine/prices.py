"""Price-snapshot store: opening and closing numbers for every market originated.

This module defines the schema and validation rules for a price snapshot. It
does not invent prices: every field is populated only from a captured quote
with a timestamp, operator, jurisdiction, market, line and decimal price. Until
a licensed or permissioned quote source exists, every numeric cell stays blank.

No network calls. No inferred values. Fail closed on any missing required field.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Optional


class MarketType(Enum):
    MONEYLINE = 'MONEYLINE'
    SPREAD = 'SPREAD'
    TOTAL = 'TOTAL'


class Side(Enum):
    HOME = 'HOME'
    AWAY = 'AWAY'
    OVER = 'OVER'
    UNDER = 'UNDER'


@dataclass(frozen=True)
class PriceSnapshot:
    """A single timestamped quote for one side of one market on one game.

    Fields are ordered as they must appear in any export: game, market, side,
    line, price, timestamps, source. A snapshot with any required field missing
    is invalid and must not be written to the store.
    """

    game_id: str
    market: MarketType
    side: Side
    line: Optional[float]  # None for moneyline (no handicap/total)
    decimal_price: float
    quote_utc: str  # ISO-8601 UTC capture time
    operator: str
    jurisdiction: str
    opening_utc: Optional[str] = None  # when this market first opened
    closing_utc: Optional[str] = None  # when this market closed (if known)
    is_closing: bool = False  # True if this is the closing snapshot for this market/side
    settlement_rule: Optional[str] = None  # operator citation for push/void handling

    def __post_init__(self):
        # Required fields: none may be blank
        if not self.game_id or not self.game_id.strip():
            raise ValueError('game_id is required')
        if self.decimal_price <= 1:
            raise ValueError('decimal_price must exceed 1')
        if not self.quote_utc or not self.quote_utc.strip():
            raise ValueError('quote_utc is required')
        if not self.operator or not self.operator.strip():
            raise ValueError('operator is required')
        if not self.jurisdiction or not self.jurisdiction.strip():
            raise ValueError('jurisdiction is required')
        # Validate ISO-8601 UTC
        datetime.fromisoformat(self.quote_utc.replace('Z', '+00:00'))
        if self.opening_utc:
            datetime.fromisoformat(self.opening_utc.replace('Z', '+00:00'))
        if self.closing_utc:
            datetime.fromisoformat(self.closing_utc.replace('Z', '+00:00'))
        # Line required for spread/total, absent for moneyline
        if self.market in (MarketType.SPREAD, MarketType.TOTAL):
            if self.line is None:
                raise ValueError(f'{self.market.value} requires a line value')
        if self.market == MarketType.MONEYLINE and self.line is not None:
            raise ValueError('moneyline has no line value')

    def american_odds(self) -> int:
        """Convert decimal price to American odds, rounding to nearest integer."""
        d = self.decimal_price
        if d >= 2:
            return int(round((d - 1) * 100))
        return int(round(-100 / (d - 1)))

    def fair_decimal_from_probability(self, win_prob: float) -> Optional[float]:
        """Fair decimal price implied by a modelled win probability.

        Returns None when win_prob is 0 (no finite fair price).
        """
        if win_prob <= 0 or win_prob >= 1:
            return None
        return 1.0 + (1.0 - win_prob) / win_prob

    def ev_at_price(self, win_prob: float, push_prob: float = 0.0, cost: float = 0.0) -> float:
        """Expected value per unit at this quote, given modelled probabilities.

        Push refunds stake (net zero on the bet). A push reduces both win and
        loss mass proportionally: effective win = win_prob, effective loss =
        1 - win_prob - push_prob.
        """
        effective_loss = 1.0 - win_prob - push_prob
        if effective_loss < 0:
            raise ValueError('win + push probability exceeds 1')
        return win_prob * (self.decimal_price - 1) - effective_loss - cost


@dataclass
class PriceStore:
    """In-memory collection of price snapshots, keyed by (game_id, market, side).

    Provides opening and closing lookups per market. Closing is the snapshot
    with the latest quote_utc for a given market/side combination; opening is
    the earliest. A snapshot flagged is_closing takes precedence as close.
    """

    def __init__(self):
        self._snapshots: list[PriceSnapshot] = []

    def add(self, snapshot: PriceSnapshot) -> None:
        self._snapshots.append(snapshot)

    def by_game_market_side(
        self, game_id: str, market: MarketType, side: Side
    ) -> list[PriceSnapshot]:
        return [
            s
            for s in self._snapshots
            if s.game_id == game_id and s.market == market and s.side == side
        ]

    def opening(self, game_id: str, market: MarketType, side: Side) -> Optional[PriceSnapshot]:
        snaps = self.by_game_market_side(game_id, market, side)
        if not snaps:
            return None
        return min(snaps, key=lambda s: s.quote_utc)

    def closing(self, game_id: str, market: MarketType, side: Side) -> Optional[PriceSnapshot]:
        snaps = self.by_game_market_side(game_id, market, side)
        if not snaps:
            return None
        flagged = [s for s in snaps if s.is_closing]
        if flagged:
            return max(flagged, key=lambda s: s.quote_utc)
        return max(snaps, key=lambda s: s.quote_utc)

    def markets_for_game(self, game_id: str) -> list[tuple[MarketType, Side]]:
        seen = set()
        for s in self._snapshots:
            if s.game_id == game_id:
                seen.add((s.market, s.side))
        return sorted(seen, key=lambda x: (x[0].value, x[1].value))

    def all_games(self) -> list[str]:
        return sorted({s.game_id for s in self._snapshots})

    def count(self) -> int:
        return len(self._snapshots)

    def missing_fields_report(self) -> dict:
        """Count snapshots missing any optional field, for the audit page."""
        report: dict = {
            'total': len(self._snapshots),
            'missing_opening': 0,
            'missing_closing': 0,
            'missing_settlement_rule': 0,
            'games_with_any_price': 0,
            'markets_with_both_open_and_close': 0,
        }
        games_with_price = set()
        for s in self._snapshots:
            if not s.opening_utc:
                report['missing_opening'] += 1
            if not s.closing_utc:
                report['missing_closing'] += 1
            if not s.settlement_rule:
                report['missing_settlement_rule'] += 1
            games_with_price.add(s.game_id)
        report['games_with_any_price'] = len(games_with_price)

        # Markets with both open and close: count distinct (game, market, side)
        # where open != close (i.e., at least two snapshots).
        groups: dict[tuple[str, MarketType, Side], list[PriceSnapshot]] = {}
        for s in self._snapshots:
            groups.setdefault((s.game_id, s.market, s.side), []).append(s)
        multi = sum(1 for v in groups.values() if len(v) >= 2)
        report['markets_with_both_open_and_close'] = multi
        return report


def load_price_snapshots_from_csv(path: Path) -> PriceStore:
    """Load snapshots from a CSV with the documented header.

    Expected columns:
      game_id,market,side,line,decimal_price,quote_utc,operator,jurisdiction,
      opening_utc,closing_utc,is_closing,settlement_rule

    Rows with any missing required field raise ValueError (fail closed).
    Rows missing only optional fields are kept with None/False defaults.
    """
    import csv

    store = PriceStore()
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        required = {
            'game_id', 'market', 'side', 'decimal_price',
            'quote_utc', 'operator', 'jurisdiction',
        }
        missing_cols = required - set(reader.fieldnames or [])
        if missing_cols:
            raise ValueError(f'price snapshot CSV missing columns: {sorted(missing_cols)}')
        for row_num, row in enumerate(reader, start=2):
            try:
                market = MarketType(row['market'].strip().upper())
                side = Side(row['side'].strip().upper())
                line_raw = (row.get('line') or '').strip()
                line = float(line_raw) if line_raw else None
                dp_raw = (row.get('decimal_price') or '').strip()
                decimal_price = float(dp_raw) if dp_raw else float('nan')
                snapshot = PriceSnapshot(
                    game_id=row['game_id'].strip(),
                    market=market,
                    side=side,
                    line=line,
                    decimal_price=decimal_price,
                    quote_utc=row['quote_utc'].strip(),
                    operator=row['operator'].strip(),
                    jurisdiction=row['jurisdiction'].strip(),
                    opening_utc=(row.get('opening_utc') or '').strip() or None,
                    closing_utc=(row.get('closing_utc') or '').strip() or None,
                    is_closing=(row.get('is_closing') or '').strip().lower() == 'true',
                    settlement_rule=(row.get('settlement_rule') or '').strip() or None,
                )
                store.add(snapshot)
            except (ValueError, KeyError, InvalidOperation) as exc:
                raise ValueError(f'price snapshot row {row_num} invalid: {exc}') from exc
    return store