"""How deep the replacement is, not merely that one exists.

Why "a starter is out" is the wrong unit
----------------------------------------
One word — *out* — hides the only variation that matters. A team missing a first-string left
tackle who hands in a competent second is not in the same state as a team whose second string is
also out and whose chart stops there. Counting absences scores those two clubs identically;
counting **strings travelled** does not.

What this module computes
-------------------------
`strings_travelled`  the published-order distance from the vacated slot to the player who actually
                     moves in, walking past teammates who are themselves unavailable.
`depth_from_top`     the same distance measured from the top of the chart, which is what "second
                     string" would mean if anyone certified it.
`chart_exhausted`    the vacated slot has no listed player beneath it. Depth becomes unknown, and
                     unknown is not zero — treating it as zero would rate a team with no backup at
                     all as a team with a replacement one deep.
`shared_backup`      one player is the only published cover for two vacated slots, so one of the
                     two vacancies has no real replacement however deep the chart looks.
`conditional`        the vacated player is Questionable, so the whole substitution is contingent on
                     a decision the injury report does not make.

What it never does
------------------
It does not invent a tier. A club with no retrieved chart gets `depth = None` and the reason
`no published chart retrieved for this club`, and no label of any kind is attached to its players.
Club charts are self-published and, on the clubs checked, labelled unofficial; they order players,
they do not certify who plays. Nothing here converts an ordering into a probability, a weight, or
an edge.
"""
from engine.snapshots import SnapshotError

#: Statuses that mean the player will not play, per the league's own published definitions.
UNAVAILABLE = ('Out', 'Doubtful')
#: Statuses that mean the substitution may or may not happen.
CONDITIONAL = ('Questionable',)
#: The published string labels, in chart order. Used for display of a *sourced* column only.
STRINGS = ('1st', '2nd', '3rd', '4th', '5th')


class ReplacementError(ValueError):
    pass


def normalize_chart(chart):
    """Accept either {'slot','unit','order':[names]} rows or plain tuples; reject malformed depth."""
    out = []
    for index, item in enumerate(chart, 1):
        if isinstance(item, dict):
            row = dict(item)
        elif isinstance(item, (tuple, list)) and len(item) == 4:
            team, unit, slot, order = item
            row = {'team': team, 'unit': unit, 'slot': slot, 'order': list(order)}
        else:
            raise ReplacementError(f'chart row {index}: expected a mapping or '
                                   '(team, unit, slot, order)')
        for field in ('team', 'slot', 'order'):
            if not row.get(field):
                raise ReplacementError(f'chart row {index}: {field} is required')
        if not isinstance(row['order'], (list, tuple)):
            raise ReplacementError(f'chart row {index}: order must be a list of names in published '
                                   'column order')
        row['order'] = list(row['order'])
        if len(set(row['order'])) != len(row['order']):
            duplicates = sorted({n for n in row['order'] if row['order'].count(n) > 1})
            raise ReplacementError(f'chart row {index}: {row["slot"]} lists '
                                   f'{", ".join(duplicates)} twice')
        out.append(row)
    return out


def statuses_by_player(report):
    """Game status per player from the league report rows. Blank means no designation, not healthy."""
    out = {}
    for row in report:
        if isinstance(row, dict):
            team, player, status = row['team'], row['player'], row.get('game_status')
        else:
            team, player, _position, _injury, _practice, status = row[:6]
        if player in out and out[player] != status:
            raise ReplacementError(f'{player}: the report carries two different game statuses '
                                   f'({out[player]!r} and {status!r}); refusing to pick one')
        out[player] = status
    return out


def unavailable_set(report, *, include_conditional=False):
    statuses = UNAVAILABLE + (CONDITIONAL if include_conditional else ())
    return {player for player, status in statuses_by_player(report).items() if status in statuses}


def evaluate(chart, report, *, include_conditional=False):
    """One row per vacated slot, with the depth of the player who replaces them.

    `include_conditional` controls whether Questionable counts as a vacancy. It defaults to False
    because a Questionable starter is a probability the report does not publish, and folding
    conditionals into the headline count would present a guess as an absence. They are still
    reported, in `conditional_slots`, so a reader can see what could yet change.
    """
    statuses = statuses_by_player(report)
    unavailable = {p for p, s in statuses.items() if s in UNAVAILABLE
                   or (include_conditional and s in CONDITIONAL)}
    conditional = set() if include_conditional else {p for p, s in statuses.items()
                                                     if s in CONDITIONAL}
    entries = normalize_chart(chart)
    entries_by_team_all = entries
    by_team = {}
    for entry in entries:
        by_team.setdefault(entry['team'], []).append(entry)
    teams_with_charts = set(by_team)

    rows = []
    for team, team_entries in sorted(by_team.items()):
        for entry in team_entries:
            order = entry['order']
            vacated = [i for i, name in enumerate(order) if name in unavailable]
            conditional_here = [order[i] for i, name in enumerate(order) if name in conditional]
            for slot_index in vacated:
                # Walk down the published order past anyone else who cannot play. This is the step a
                # "who is out" count never takes: the replacement is not the next name on the page,
                # it is the next name on the page who can actually play.
                replacement = next((j for j in range(slot_index + 1, len(order))
                                    if order[j] not in unavailable), None)
                # A Questionable name is not a answer and not a refusal: the depth depends on a
                # decision the report does not publish, so both distances are measured and stated.
                certain = next((j for j in range(slot_index + 1, len(order))
                                if order[j] not in unavailable and order[j] not in conditional), None)
                ahead_end = replacement if replacement is not None else len(order)
                conditional_ahead = [order[j] for j in range(slot_index + 1, ahead_end)
                                     if order[j] in conditional]
                depth_note = None
                if replacement is not None and order[replacement] in conditional:
                    depth_note = (f'the next name able to play, {order[replacement]}, carries a '
                                  f'{statuses.get(order[replacement])} status: depth of '
                                  f'{replacement - slot_index} if he plays'
                                  + (f', {certain - slot_index} if he does not'
                                     if certain is not None and certain != replacement else
                                     ', and no further name is listed' if certain is None else ''))
                rows.append({'team': team, 'unit': entry.get('unit'), 'slot': entry['slot'],
                             'vacated_player': order[slot_index], 'vacated_rank': slot_index + 1,
                             'vacated_status': statuses.get(order[slot_index]),
                             'replacement_player': order[replacement] if replacement is not None
                             else None,
                             'replacement_rank': replacement + 1 if replacement is not None else None,
                             'strings_travelled': (replacement - slot_index)
                             if replacement is not None else None,
                             'depth_from_top': replacement + 1 if replacement is not None else None,
                             'chart_exhausted': replacement is None,
                             'conditional_slots': conditional_here,
                             'certain_replacement': order[certain] if certain is not None else None,
                             'certain_rank': certain + 1 if certain is not None else None,
                             'certain_strings': (certain - slot_index) if certain is not None else None,
                             'conditional_ahead': conditional_ahead,
                             'depth_note': depth_note,
                             'replacement_is_conditional': bool(replacement is not None
                                                                and order[replacement] in conditional),
                             'sourced': True,
                             'reason': None if replacement is not None else
                             'chart lists no player beneath the vacated slot'})
    # A player may be the only published cover for more than one vacancy. That is not two
    # replacements; it is one replacement and an unfilled slot.
    shared = {}
    for row in rows:
        if row['replacement_player']:
            shared.setdefault((row['team'], row['replacement_player']), []).append(row['slot'])
    for row in rows:
        key = (row['team'], row['replacement_player'])
        row['shared_backup'] = shared[key] if len(shared.get(key, [])) > 1 else None

    # A player who is Out and appears on no chart row is a vacancy whose slot cannot be located.
    # Reporting nothing would silently drop exactly the cases the depth charts disagree about.
    listed = {}
    for entry in entries_by_team_all:
        for name in entry['order']:
            listed.setdefault((entry['team'], name), []).append(entry['slot'])
    for team_row in report:
        team = team_row['team'] if isinstance(team_row, dict) else team_row[0]
        player = team_row['player'] if isinstance(team_row, dict) else team_row[1]
        status = (team_row.get('game_status') if isinstance(team_row, dict) else team_row[5])
        if team not in teams_with_charts or status not in UNAVAILABLE:
            continue
        if (team, player) not in listed:
            rows.append({'team': team, 'unit': None, 'slot': None, 'vacated_player': player,
                         'vacated_rank': None, 'vacated_status': status, 'replacement_player': None,
                         'replacement_rank': None, 'strings_travelled': None, 'depth_from_top': None,
                         'chart_exhausted': None, 'conditional_slots': [], 'shared_backup': None,
                         'certain_replacement': None, 'certain_rank': None, 'certain_strings': None,
                         'conditional_ahead': [], 'depth_note': None,
                         'replacement_is_conditional': False,
                         'sourced': False,
                         'reason': f'{player} carries an {status} game status but appears on no row of '
                                   'the retrieved chart; the vacated slot cannot be located, so depth '
                                   'is unknown'})
    # One player listed as the next string beneath two different slots is a structural single point
    # of failure, whether or not both slots are vacant this week.
    for (team, player), slots in sorted(listed.items()):
        if len(slots) > 1:
            for row in rows:
                if row.get('team') == team and row.get('replacement_player') == player:
                    row['covers_slots'] = slots

    for team in sorted({(r['team'] if isinstance(r, dict) else r[0]) for r in report}
                       - teams_with_charts):
        rows.append({'team': team, 'unit': None, 'slot': None, 'vacated_player': None,
                     'vacated_rank': None, 'vacated_status': None, 'replacement_player': None,
                     'replacement_rank': None, 'strings_travelled': None, 'depth_from_top': None,
                     'chart_exhausted': None, 'conditional_slots': [], 'shared_backup': None,
                     'certain_replacement': None, 'certain_rank': None, 'certain_strings': None,
                     'conditional_ahead': [], 'depth_note': None,
                     'replacement_is_conditional': False,
                     'sourced': False,
                     'reason': f'no published chart retrieved for {team}; depth is unknown, not zero'})
    return rows


def unit_rollup(rows):
    """Per team and unit: vacancies, depth sum, and how much of it is unknown.

    `depth_known_share` is the honest denominator. A club whose chart was never retrieved shows
    zero known depth across every slot, and a rollup that omitted the share would make that club
    look deep rather than unmeasured.
    """
    grouped = {}
    for row in rows:
        if row['slot'] is None:
            continue
        key = (row['team'], row.get('unit') or 'unlabelled')
        grouped.setdefault(key, []).append(row)
    out = []
    for (team, unit), items in sorted(grouped.items()):
        depths = [i['strings_travelled'] for i in items if i['strings_travelled'] is not None]
        _ = depths  # kept named for the reader: headline depth uses only located, non-null distances
        out.append({'team': team, 'unit': unit, 'vacancies': len(items),
                    'depth_total': sum(depths) if depths else None,
                    'max_depth': max(depths) if depths else None,
                    'deepest_slot': max(items, key=lambda i: i['strings_travelled'] or -1)['slot']
                    if depths else None,
                    'exhausted_slots': sum(1 for i in items if i['chart_exhausted']),
                    'shared_backups': len({tuple(i['shared_backup']) for i in items
                                           if i['shared_backup']}),
                    'depth_known': len(depths),
                    'depth_unknown': len(items) - len(depths),
                    'depth_known_share': round(len(depths) / len(items), 4) if items else None,
                    # The second number is the depth if every conditional name ahead declines. It is
                    # a distance, not a scenario weight: no probability is attached to it anywhere.
                    'worst_case_max_depth': max([i['certain_strings'] or i['strings_travelled']
                                                 for i in items
                                                 if (i['certain_strings'] or i['strings_travelled'])]
                                                or [None]),
                    'conditional_vacancies': sum(1 for i in items if i['replacement_is_conditional']),
                    'chart_exhausted_below': sum(1 for i in items
                                                 if i['replacement_is_conditional']
                                                 and i['certain_strings'] is None)})
    return out


def string_label(rank):
    """Display a *sourced* rank as a string label. Refuses to guess."""
    if rank is None:
        return ''
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1 or rank > len(STRINGS):
        raise ReplacementError(f'no published string label for rank {rank!r}')
    return STRINGS[rank - 1]


def limits():
    """The published caveats, as rows, so the page cannot be read as a certified depth record."""
    return [
        ('Chart order is not a game-day record', 'A club chart lists who is next in the pecking '
         'order on the day it was published. Lines, packages and inactive lists are decided later, '
         'and this project has no certified per-game depth source.'),
        ('Club charts self-declare unofficial', 'The Chiefs and Lions pages retrieved 2026-11-14 '
         'carry the wording "Unofficial Depth Chart" in their own headings. A source that labels '
         'itself unofficial is used for ordering and cited, never upgraded.'),
        ('Distance is not damage', 'Two strings deep is a count, not a value. No performance drop '
         'per string is estimated here, because no verified starter-versus-replacement production '
         'sample exists in this repository.'),
        ('No per-play denominator', 'The league publishes eleven statistics categories and none of '
         'them is snaps or participation, so a replacement who takes over half the reps and one who '
         'takes five look identical to the data available.'),
        ('Conditional is not absent', 'A Questionable starter generates no vacancy row by default. '
         'Turning a probability the report does not publish into a certain absence would inflate '
         'every count.'),
    ]


if __name__ == '__main__':  # pragma: no cover
    import json
    chart = [{'team': 'SEA', 'unit': 'Offense', 'slot': 'QB',
              'order': ['Sam Darnold', 'Drew Lock', 'Jalen Milroe']},
             {'team': 'SEA', 'unit': 'Offense', 'slot': 'LT',
              'order': ['Charles Cross', 'Josh Jones']}]
    report = [{'team': 'SEA', 'player': 'Sam Darnold', 'position': 'QB', 'injuries': ['Ribs'],
               'practice_status': 'Did Not Participate In Practice', 'game_status': 'Out'},
              {'team': 'SEA', 'player': 'Charles Cross', 'position': 'T', 'injuries': ['Ankle'],
               'practice_status': 'Did Not Participate In Practice', 'game_status': 'Out'}]
    rows = evaluate(chart, report)
    print(json.dumps({'rows': rows, 'rollup': unit_rollup(rows)}, indent=2))
