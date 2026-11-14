"""Line origination pipeline: side first, then total, then moneyline.

This module defines the origination order and the fair-line extraction logic.
No NFL numerical value is produced here: every output is blank until a verified
joint score distribution and executable market prices exist.

The pipeline stages are:
  1. Game universe — stable key, kickoff, both clubs
  2. Availability state — participation, game status, reserve moves (timestamped)
  3. Unit priors — team scoring/possession from official statistics
  4. Joint score distribution — penalised-likelihood grid over home/away scores
  5. Fair line extraction — spread, total, moneyline from the joint distribution
  6. Market comparison — proportional de-vig of inverse decimal prices
  7. Quote and abstain — publish fair line with uncertainty band, withhold on gaps
  8. Replay and score — proper scoring against settled outcomes under the seven gates

Stage 5 publishes three separate columns: fair line, market line, difference.
Until inputs exist, all columns stay blank.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OriginationStage(Enum):
    GAME_UNIVERSE = 'game_universe'
    AVAILABILITY = 'availability'
    UNIT_PRIORS = 'unit_priors'
    JOINT_DISTRIBUTION = 'joint_distribution'
    FAIR_LINE = 'fair_line'
    MARKET_COMPARISON = 'market_comparison'
    QUOTE_AND_ABSTAIN = 'quote_and_abstain'
    REPLAY_AND_SCORE = 'replay_and_score'


@dataclass
class FairLineColumns:
    """The three columns published side by side for each market.

    fair_line   — model-derived fair line from the joint distribution
    market_line — market line from proportional de-vig of executable quotes
    difference  — fair_line − market_line (positive = model sees more value
                   than the market price implies)

    All three are None until the corresponding inputs are verified. None is not
    zero; it means the value cannot be computed yet.
    """

    fair_line: Optional[float]
    market_line: Optional[float]
    difference: Optional[float]

    def is_complete(self) -> bool:
        return all(v is not None for v in (self.fair_line, self.market_line, self.difference))


@dataclass
class OriginationRecord:
    """One game's origination record across all three markets.

    Published as: fair spread / market spread / spread difference,
                  fair total / market total / total difference,
                  fair moneyline / market moneyline / moneyline difference.
    """

    game_id: str
    kickoff_utc: Optional[str]
    home_team: str
    away_team: str
    stage_reached: OriginationStage
    spread: FairLineColumns
    total: FairLineColumns
    moneyline_home: FairLineColumns
    moneyline_away: FairLineColumns
    notes: list[str]

    def blank_columns(self) -> list[str]:
        """Return column names whose value is None, for the audit page."""
        blank = []
        for market_name, cols in (
            ('spread', self.spread),
            ('total', self.total),
            ('moneyline_home', self.moneyline_home),
            ('moneyline_away', self.moneyline_away),
        ):
            for col_name in ('fair_line', 'market_line', 'difference'):
                if getattr(cols, col_name) is None:
                    blank.append(f'{market_name}.{col_name}')
        return blank


def fair_spread_from_distribution(
    margin_pmf: dict[int, float], push_handling: str = 'refund'
) -> Optional[float]:
    """Extract the fair spread from a joint margin distribution.

    A fair spread h makes P(home_margin + h > 0) the no-push break-even win
    probability against a -110-style quote. It is not generally the mean
    margin; the push mass at each integer h must be accounted for.

    Returns None when the distribution is empty or invalid — never a guessed
    number.
    """
    if not margin_pmf:
        return None
    total = sum(margin_pmf.values())
    if abs(total - 1.0) > 1e-9:
        return None
    # Fair spread: the integer h where cover probability is closest to break-even
    # against the implied probability of a standard quote. Without a quoted
    # price, return the median-based reference instead of asserting a fair line.
    margins = sorted(margin_pmf)
    cumulative = 0.0
    for m in margins:
        cumulative += margin_pmf[m]
        if cumulative >= 0.5 - 1e-12:
            # Median margin: home covers at h = -median (home favourite gives points)
            return float(-m)
    return None


def fair_total_from_distribution(total_pmf: dict[int, float]) -> Optional[float]:
    """Extract the fair total from a joint total-points distribution.

    Returns the median total (mass at or below equals mass at or above),
    retaining equality as a separate push state. None when the distribution
    is empty or invalid.
    """
    if not total_pmf:
        return None
    total = sum(total_pmf.values())
    if abs(total - 1.0) > 1e-9:
        return None
    totals = sorted(total_pmf)
    cumulative = 0.0
    for t in totals:
        cumulative += total_pmf[t]
        if cumulative >= 0.5 - 1e-12:
            return float(t)
    return None


def fair_moneyline_from_distribution(home_win_prob: float) -> Optional[float]:
    """Fair decimal moneyline for the home team from modelled win probability.

    Returns None when win_prob is 0 or 1 (no finite fair price), or when
    win_prob is None.
    """
    if home_win_prob is None or home_win_prob <= 0 or home_win_prob >= 1:
        return None
    return 1.0 + (1.0 - home_win_prob) / home_win_prob


def market_line_from_prices(decimal_prices: list[float]) -> Optional[float]:
    """Proportional de-vig of inverse decimal prices over exhaustive outcomes.

    This is the market-implied probability normalised to sum to 1. Used as the
    market_line input for comparison with fair_line. None when any price is
    invalid or when fewer than two outcomes exist.
    """
    if len(decimal_prices) < 2:
        return None
    if any(p <= 1 for p in decimal_prices):
        return None
    inv = [1.0 / p for p in decimal_prices]
    total_inv = sum(inv)
    if total_inv <= 0:
        return None
    # Return the normalised implied probability of the first outcome as the
    # market-line proxy; the full vector is the de-vigged distribution.
    return inv[0] / total_inv


def difference(fair: Optional[float], market: Optional[float]) -> Optional[float]:
    """fair − market. None when either input is None — never imputed."""
    if fair is None or market is None:
        return None
    return fair - market


def origination_order() -> list[str]:
    """The mandated origination sequence, in order."""
    return [
        'side (spread / handicap)',
        'total (over / under)',
        'moneyline',
    ]