"""Verified results feed: official outcomes for backtest and ROI computation.

This module defines the schema and validation rules for a verified game result.
Results are populated only from official NFL publications (game centers, Game
Books, schedules). No value is inferred: if a score or outcome is not confirmed
by an official source, the field stays blank.

No network calls. No inferred values. Fail closed on any missing required field.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class GameStatus(Enum):
    SCHEDULED = 'SCHEDULED'
    IN_PROGRESS = 'IN_PROGRESS'
    FINAL = 'FINAL'
    POSTPONED = 'POSTPONED'
    CANCELLED = 'CANCELLED'


class SettlementState(Enum):
    WIN = 'WIN'
    LOSS = 'LOSS'
    PUSH = 'PUSH'
    VOID = 'VOID'


@dataclass(frozen=True)
class VerifiedResult:
    """A single officially verified game result.

    Required fields: game_id, season, week, home_team, away_team,
    home_score, away_score, status, source_url, retrieved_utc.
    Optional fields: overtime, total_line, spread_line, moneyline prices,
    settlement outcomes per market.
    """

    game_id: str
    season: int
    week: int
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: GameStatus
    source_url: str
    retrieved_utc: str  # ISO-8601 UTC capture time
    overtime: bool = False
    total_line: Optional[float] = None
    spread_line: Optional[float] = None  # home spread, negative = home favorite
    settlement: dict[str, SettlementState] = field(default_factory=dict)

    def __post_init__(self):
        if not self.game_id or not self.game_id.strip():
            raise ValueError('game_id is required')
        if self.season < 1920 or self.season > 2100:
            raise ValueError('season out of range')
        if self.week < 1 or self.week > 22:
            raise ValueError('week out of range')
        if not self.home_team or not self.away_team:
            raise ValueError('both teams required')
        if self.status == GameStatus.FINAL:
            if self.home_score is None or self.away_score is None:
                raise ValueError('final game requires both scores')
        if not self.source_url or not self.source_url.strip():
            raise ValueError('source_url is required')
        if not self.retrieved_utc or not self.retrieved_utc.strip():
            raise ValueError('retrieved_utc is required')

    @property
    def margin(self) -> Optional[int]:
        """Home margin (home_score - away_score), or None if not final."""
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score - self.away_score

    @property
    def total_points(self) -> Optional[int]:
        """Combined points, or None if not final."""
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score + self.away_score

    def settlement_for(self, market: str, side: str) -> Optional[SettlementState]:
        """Look up the settlement state for a market/side combination."""
        return self.settlement.get(f'{market}:{side}')


@dataclass
class ResultsFeed:
    """Collection of verified results, keyed by game_id.

    Provides lookup by game and summary statistics for the audit page.
    """

    def __init__(self):
        self._results: dict[str, VerifiedResult] = {}

    def add(self, result: VerifiedResult) -> None:
        self._results[result.game_id] = result

    def get(self, game_id: str) -> Optional[VerifiedResult]:
        return self._results.get(game_id)

    def final_games(self) -> list[VerifiedResult]:
        return [r for r in self._results.values() if r.status == GameStatus.FINAL]

    def count(self) -> int:
        return len(self._results)

    def count_final(self) -> int:
        return len(self.final_games())

    def missing_scores(self) -> list[str]:
        """Game IDs that are FINAL but lack one or both scores."""
        return [
            r.game_id
            for r in self._results.values()
            if r.status == GameStatus.FINAL
            and (r.home_score is None or r.away_score is None)
        ]

    def coverage_report(self) -> dict:
        """Summary of coverage for the audit page."""
        final = self.final_games()
        return {
            'total_games': len(self._results),
            'final_games': len(final),
            'games_missing_scores': len(self.missing_scores()),
            'seasons': sorted({r.season for r in self._results.values()}),
            'weeks': sorted({r.week for r in self._results.values()}),
            'teams': sorted(
                {t for r in self._results.values() for t in (r.home_team, r.away_team)}
            ),
        }


def load_verified_results_from_csv(path: Path) -> ResultsFeed:
    """Load results from CSV.

    Expected columns:
      game_id,season,week,home_team,away_team,home_score,away_score,status,
      source_url,retrieved_utc,overtime,total_line,spread_line

    Rows missing required fields raise ValueError. Scores may be blank for
    non-final games; blank scores on a FINAL row are an error.
    """
    import csv

    feed = ResultsFeed()
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        required = {
            'game_id', 'season', 'week', 'home_team', 'away_team',
            'status', 'source_url', 'retrieved_utc',
        }
        missing_cols = required - set(reader.fieldnames or [])
        if missing_cols:
            raise ValueError(f'results CSV missing columns: {sorted(missing_cols)}')
        for row_num, row in enumerate(reader, start=2):
            try:
                home_raw = (row.get('home_score') or '').strip()
                away_raw = (row.get('away_score') or '').strip()
                home_score = int(home_raw) if home_raw else None
                away_score = int(away_raw) if away_raw else None
                status = GameStatus(row['status'].strip().upper())
                result = VerifiedResult(
                    game_id=row['game_id'].strip(),
                    season=int(row['season'].strip()),
                    week=int(row['week'].strip()),
                    home_team=row['home_team'].strip(),
                    away_team=row['away_team'].strip(),
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    source_url=row['source_url'].strip(),
                    retrieved_utc=row['retrieved_utc'].strip(),
                    overtime=(row.get('overtime') or '').strip().lower() == 'true',
                    total_line=float(row['total_line'].strip())
                    if (row.get('total_line') or '').strip()
                    else None,
                    spread_line=float(row['spread_line'].strip())
                    if (row.get('spread_line') or '').strip()
                    else None,
                )
                feed.add(result)
            except (ValueError, KeyError) as exc:
                raise ValueError(f'results row {row_num} invalid: {exc}') from exc
    return feed