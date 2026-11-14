"""Replacement-depth register.

The requirement is not "was there a replacement" but "how deep is the
replacement". A second-string replacement and a fourth-string replacement are
different events, and only a published depth ordering can tell them apart.

The NFL publishes no official game-day depth chart, so every tier here is read
from a club publication that labels itself unofficial. Tiers are recorded as
printed; no tier is inferred, filled in or promoted.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARTS = json.loads((ROOT / 'evidence' / 'depth_charts.json').read_text())

TIER_LABELS = {1: '1st string', 2: '2nd string', 3: '3rd string', 4: '4th string'}


def depth_rows():
    """One row per printed slot-player pair, with the tier as published."""
    rows = []
    for chart in CHARTS['charts']:
        for unit, slots in chart['units'].items():
            for position, players in slots:
                for tier, player in enumerate(players, start=1):
                    if not player:
                        continue
                    rows.append({
                        'club': chart['club'], 'club_name': chart['club_name'],
                        'unit': unit, 'position': position, 'player': player,
                        'tier': tier, 'tier_label': TIER_LABELS[tier],
                        'source_id': chart['source_id'],
                        'official_status': chart['official_status'],
                    })
    return rows


def player_slots(chart, player):
    """Every slot a player occupies, with the tier printed for each."""
    found = []
    for unit, slots in chart['units'].items():
        for index, (position, players) in enumerate(slots):
            for tier, name in enumerate(players, start=1):
                if name == player:
                    found.append({'unit': unit, 'position': position,
                                  'slot_index': index, 'tier': tier,
                                  'players': players})
    return found


def deficiency_rows():
    """For each ruled-out player: which slot, who replaces them, how deep."""
    status = CHARTS['week10_status']
    by_club = {c['club']: c for c in CHARTS['charts']}
    out_rows = []
    for entry in status['players']:
        club, player = entry['club'], entry['player']
        chart = by_club.get(club)
        base = {
            'club': club, 'player': player, 'position': entry['position'],
            'game_status': entry['game_status'],
            'unit': '', 'slot': '', 'injured_tier': None, 'injured_tier_label': '',
            'replacement': '', 'replacement_tier': None, 'replacement_tier_label': '',
            'next_after_replacement': '', 'note': '',
            'injury_source_id': status['source_id'], 'chart_source_id': '',
        }
        if chart is None:
            base['note'] = 'no club depth chart retrieved for this club'
            base['replacement'] = ''
            out_rows.append(base)
            continue
        slots = player_slots(chart, player)
        if not slots:
            base['note'] = ('player is ruled out but does not appear on the club '
                            'depth chart; the depth of the replacement cannot be '
                            'read from any published source')
            base['chart_source_id'] = chart['source_id']
            out_rows.append(base)
            continue
        for slot in slots:
            row = dict(base)
            row['unit'] = slot['unit']
            row['slot'] = slot['position']
            row['injured_tier'] = slot['tier']
            row['injured_tier_label'] = TIER_LABELS[slot['tier']]
            row['chart_source_id'] = chart['source_id']
            deeper = [(tier, name) for tier, name in enumerate(slot['players'], start=1)
                      if tier > slot['tier'] and name]
            ruled_out = {p['player'] for p in status['players']
                         if p['club'] == club and p['player'] != player}
            usable = [(t, n) for t, n in deeper if n not in ruled_out]
            if not deeper:
                row['note'] = 'no deeper player is printed at this slot'
            elif not usable:
                row['note'] = ('every deeper player printed at this slot is also '
                               'ruled out')
                row['replacement'] = deeper[0][1]
                row['replacement_tier'] = deeper[0][0]
                row['replacement_tier_label'] = TIER_LABELS[deeper[0][0]]
            else:
                row['replacement'] = usable[0][1]
                row['replacement_tier'] = usable[0][0]
                row['replacement_tier_label'] = TIER_LABELS[usable[0][0]]
                rest = [n for _, n in usable[1:]]
                row['next_after_replacement'] = rest[0] if rest else ''
                if len(usable) == 1:
                    row['note'] = 'no further listed cover behind the replacement'
            out_rows.append(row)
    return out_rows


def coverage():
    """Which clubs in the Week 10 official report have a chart this session read."""
    have = {c['club'] for c in CHARTS['charts']}
    clubs = sorted({p['club'] for p in CHARTS['week10_status']['players']})
    return [{'club': club, 'chart_retrieved': club in have} for club in clubs]
