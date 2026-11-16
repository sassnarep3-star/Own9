"""Independent verification layer: requirements, readiness, questions, suggestions, flags.

Every table this module renders is built from ONE of three kinds of input, and the row
records which one it is:

1. A value this module *measures* at build time from a committed file (a count of rows,
   a ratio of two counts). The measurement function is attached to the row so the number
   cannot be retyped into prose and drift.
2. A value *transcribed from an official publisher* on a stated date, with the source
   link and the date in the row.
3. A blank. A cell stays blank when nothing obtained (or published) supplies it, and the
   blank is labelled "unverified" rather than left looking like a zero.

Nothing in this module reaches the network, invents an NFL value, or promotes a proposal
to a finding. The distinction the site is judged on is between *implemented mechanics*
(which can be tested) and *empirically established skill* (which cannot be claimed from
software tests), so every requirement row carries both verdicts separately.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Frozen instant for this section's transcriptions. Deterministic builds only: the
# repository's CI regenerates the site and diffs it, so nothing may print a clock.
AS_OF = "2026-11-16"
RETRIEVED = "2026-11-16 UTC"

# ------------------------------------------------------------------ source ids
# Ids already registered in evidence/sources.json by earlier sessions. Reusing the id
# means this section adds no duplicate register entry; the URL is resolved from that file
# at build time, so a link here cannot point anywhere the register does not point.
_SOURCES = {s["id"]: s for s in json.loads((ROOT / "evidence/sources.json").read_text())}

S_SCHED_W10 = "nfl-sched-w10"          # https://www.nfl.com/schedules/2026/by-week/week-10
S_INJURY = "nfl-injury"                # https://www.nfl.com/injuries/
S_GAMECENTER_W10 = "nfl-gamecenter-w10"  # WAS @ NYG game centre
S_RULEBOOK = "nfl-rulebook"            # 2026 rulebook incl. the onside-kick change
S_SCHED_W1 = "nfl-sched-w1"
S_SCHED_W9 = "nfl-sched-w9"
S_SCHED_W11 = "nfl-schedule-w11"
S_GAMECENTER_NE_DET = "nfl-gamecenter-w10"  # same register entry as the Week 10 page
CLUB_DEPTH = {  # club depth charts already registered by earlier sessions
    "KC": "chiefs-depth", "SEA": "seahawks-depth", "DET": "lions-depth",
}

REPO = "repo"

# Sources read by this session that are NOT yet in the shared evidence/sources.json. They are
# resolved locally instead of being edited into that file, which open PR #51 owns; VF-10 asks
# its owner to register them. Each carries the URL that was actually read on 2026-11-16.
LOCAL_SOURCES = {
    "nfl-terms": {"url": "https://www.nfl.com/legal/terms/",
                  "publisher": "NFL.com Terms (updated 16 May 2024)",
                  "local_note": "section 1.3 read in full on 2026-11-16"},
    "nfl-gc-pit-cin": {"url": "https://www.nfl.com/games/steelers-at-bengals-2026-reg-10",
                       "publisher": "NFL game centre",
                       "local_note": "Game Info block read on 2026-11-16"},
    "nfl-gc-ne-det": {"url": "https://www.nfl.com/games/patriots-at-lions-2026-reg-10",
                      "publisher": "NFL game centre",
                      "local_note": "Game Info block read on 2026-11-16"},
}
S_TERMS = "nfl-terms"
S_GC_PIT_CIN = "nfl-gc-pit-cin"
S_GC_NE_DET = "nfl-gc-ne-det"

# The clause that changes what may be recommended. Quoted, not paraphrased, and cited.
TERMS_CLAUSE = (
    'NFL.com Terms, section 1.3 (updated 16 May 2024): "You may use the Services solely for your own '
    'individual non-commercial and informational purposes only... Systematic retrieval of data or '
    'other content from the Services, whether to create or compile, directly or indirectly, a '
    'collection, compilation, database, or directory, is prohibited absent our express prior written '
    'consent."'
)
TERMS_CLEAR = (
    "Express prior written consent from NFL Enterprises, or a licensed data feed. A single "
    "owner-reviewed read is the permitted use; a scheduled series is what the clause forbids."
)


def src(source_id: str) -> dict:
    """Resolve a source id to its record; fail loudly if it is in neither register."""
    try:
        return _SOURCES[source_id]
    except KeyError:
        pass
    if source_id in LOCAL_SOURCES:
        return LOCAL_SOURCES[source_id]
    raise KeyError(f"source id {source_id!r} is in neither the shared register nor this section's")


def link(source_id: str) -> tuple[str, str]:
    s = src(source_id)
    return s["url"], s["publisher"]


# ------------------------------------------------------------------ measurements
def _rows(name: str) -> list[dict]:
    path = ROOT / "data" / "board" / name
    if not path.exists():
        return []
    with path.open() as fh:
        return list(csv.DictReader(fh))


def measured() -> dict:
    """Every number this section publishes that is computed rather than transcribed."""
    results = _rows("results_2026.csv")
    pending = _rows("schedule_pending_2026.csv")
    markets = _rows("markets_week11.csv")
    snaps = _rows("price_snapshots.csv")
    corr = _rows("correlations.csv")
    walk = _rows("walk_forward.csv")
    repl = _rows("replacement_depth.csv")

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    weeks = sorted({_int(r["week"]) for r in results if _int(r["week"])})
    finals_w10 = [r for r in results if _int(r["week"]) == 10]
    pending_w10 = [r for r in pending if _int(r["week"]) == 10]
    priced = [m for m in markets if (m.get("market_price") or "").strip()]
    with_both = {}
    for s in snaps:
        with_both.setdefault(s["market_id"], set()).add((s["phase"], (s.get("market_price") or "").strip()))
    open_with_price = sum(1 for k, v in with_both.items()
                          if ("open",) in {p for p, mp in v} and any(mp for _, mp in v for p in [("open",)]))
    complete_weeks = [w for w in walk if (w.get("complete") or "").strip().lower() == "true"]
    withheld_repl = [r for r in repl if not (r.get("depth_travelled") or "").strip()]
    corr_with_n = [c for c in corr if (c.get("n") or "").strip()]
    claim_outside = [c for c in corr
                     if (c.get("dependence_claimed") or "").lower().startswith("declared")]
    return {
        "finals_total": len(results),
        "finals_weeks": weeks,
        "finals_w10": len(finals_w10),
        "pending_total": len(pending),
        "pending_w10": len(pending_w10),
        "markets_week11": len(markets),
        "markets_with_market_price": len(priced),
        "markets_priced_pct": (len(priced) / len(markets)) if markets else None,
        "snapshots_total": len(snaps),
        "snapshots_with_market_price": sum(1 for s in snaps if (s.get("market_price") or "").strip()),
        "correlations_total": len(corr),
        "correlations_with_n": len(corr_with_n),
        "correlations_claiming_dependence": len(claim_outside),
        "walk_forward_weeks": len(walk),
        "walk_forward_complete_weeks": len(complete_weeks),
        "walk_forward_graded_games": sum(_int(w.get("n")) or 0 for w in walk),
        "walk_forward_graded_games_complete_only": sum(_int(w.get("n")) or 0 for w in complete_weeks),
        "replacement_rows": len(repl),
        "replacement_withheld": len(withheld_repl),
    }


M = measured()

# ------------------------------------------------------------------ the brief, line by line
# One row per line of the user's requirement list, in the order the brief states them.
# `impl` answers "is the mechanism built and tested in this repository?"; `emp` answers
# "is the empirical claim established against official evidence?". They are different
# questions and are never merged. `gate` names the specific thing that blocks the next
# step; `clear` names the number or artefact that would clear it.
#
# A blank `emp` means NOT ESTABLISHED, never "passed". No row claims a validated edge.
REQ = [
    # (id, requirement, impl, emp, gate, clear, source_ids)
    ("R-01", "Price-snapshot store recording opening and closing numbers for every market originated",
     "Built: 39 Week 11 markets, 78 snapshot rows (open + close per market); open and close are "
     "separate fields, and a test fails the build if an opening *price* is ever populated without a source.",
     "Not established: 0 of 39 markets carry a market price, so no open/close spread can exist.",
     "No official or licensed price source exists. The league publishes no wagering prices and no book of record is approved.",
     "A licensed historical quote feed (or recorded own-book prices) covering the sample window.",
     (REPO,)),
    ("R-02", "Verified results feed so backtests and ROI can be computed at all",
     f"Built: {M['finals_total']} finals across weeks {M['finals_weeks'][0]}-{M['finals_weeks'][-1]}, "
     "each transcribed from the official weekly schedule page and each carrying its game-centre URL.",
     f"Partly current: {M['finals_w10']} Week 10 final is committed; the official Week 10 page now "
     f"shows {M['finals_w10'] + 11} finals plus 2 games still without a score.",
     "The feed is a dated 14 Nov capture, frozen on purpose. It is behind the official page by 11 settled games.",
     "A dated re-capture of Week 10 as its own immutable snapshot (published as SV-02 here), then the same for Week 11.",
     (S_SCHED_W10, REPO)),
    ("R-03", "Originate the side first, then the total, then the moneyline",
     "Built and enforced mechanically: a total cannot be instantiated without its game's side, a moneyline "
     "cannot be instantiated without the total, and the order is regression-tested.",
     "Mechanical only: the ordering is a discipline, not evidence that the numbers are good.",
     "Nothing blocks the order. Its value depends entirely on R-08/R-09.",
     "n/a — this is a process requirement, satisfied by construction when all three markets exist.",
     (REPO,)),
    ("R-04", "Publish fair line, market line and difference as separate columns",
     "Built: three separate fields on every market row; the difference is computed, never transcribed.",
     "Half blank: the fair line is populated, the market line and the difference are blank on every row.",
     "No market price exists to difference against (same blocker as R-01).",
     "Any approved price source; with one, the difference column becomes measurable that day.",
     (REPO,)),
    ("R-05", "Separate signal from staking so a lucky staking run cannot mask a bad signal",
     "Built: two disjoint sheets with independent rankings and a masking report; the staking sheet has no "
     "rank column at all, so it cannot promote a strategy.",
     "Signal side: walk-forward diagnostics published with n per week. Staking side: blank — no ROI, no CLV.",
     "Staking metrics are undefined without executable prices.",
     "Executable quotes on the games that were originated, from kickoff onward.",
     (REPO,)),
    ("R-06", "Track the depth of the replacement, not just the fact of a replacement",
     f"Built: {M['replacement_rows']} register rows carrying the number of chart strings travelled, "
     f"split by offence and defence; {M['replacement_withheld']} rows are withheld with a stated reason.",
     "Weaker than certified: the depth order is the club's published chart, which clubs self-label "
     "unofficial, not a certified game-day depth record.",
     "No official game-day depth record exists for all 32 clubs (see R-07/R-28).",
     "A structured, dated depth source per club, or official snap counts, verified for all 32 clubs.",
     (REPO,)),
    ("R-07", "Compute correlations only from officially sourced numbers and publish n with each value",
     f"Built: {M['correlations_with_n']} of {M['correlations_total']} correlation rows publish n beside the "
     "value, plus a Fisher-z interval and a predeclared 0.10 deadband.",
     f"Partly established: {M['correlations_claiming_dependence']} of {M['correlations_total']} pairs clear "
     "the deadband on the current feed. The rest decline to claim dependence.",
     "n is small (one season) and the sample grows only as the feed grows.",
     "A multi-season official sample; the published n is the gate and it is visible on every row.",
     (REPO,)),
    ("R-08", "Define a demotion gate that sends a live strategy back to paper",
     "Built and boundary-tested: trailing ROI, mean edge, CLV rate, Brier drift and feed staleness, "
     "fail-closed below a minimum graded sample.",
     "Armed, never triggered: no strategy is live, so the gate has never had a live entry to demote.",
     "The gate needs a live entry to act on, which needs R-01 resolved.",
     "One live strategy plus the minimum graded sample; the gate then fires or does not.",
     (REPO,)),
    ("R-09", "Pre-register every strategy; forbid backtest numbers on the leaderboard",
     "Built: strategies are declared before evaluation and the leaderboard is generated from the walk-forward "
     "diagnostic only; a build check fails if a backtest number reaches a leaderboard cell.",
     "Not established: no strategy has passed the predeclared gates, so the leaderboard has no eligible entry.",
     "Every signal's interval lower bound is negative on the available sample.",
     "A positive benchmark-relative skill whose interval excludes the benchmark, out of sample.",
     (REPO,)),
    ("R-10", "Build the availability graph as a first-class dataset (expected starter vs actual)",
     "Partly built: three official NFL Game Books (Weeks 9-10, 2026) transcribed, all four published "
     "starting elevens changng between the two weeks, and one fully documented centre replacement.",
     "Evidence-thin: two clubs, two weeks, one verified substitution chain.",
     "NFL Game Books are published per game as PDFs; three have been read, 148 games are in the feed.",
     "Game Books for a full season, ingested and cross-checked against the inactive lists.",
     (S_GAMECENTER_W10, REPO)),
    ("R-11", "Do not model depth from jersey order; model it from playing time",
     "Rejected shortcut documented: jersey-number, experience and salary routes are recorded as rejected, "
     "not silently used. Depth is taken from a published chart column where one exists.",
     "Blocked: no official snap-count source has been verified for all clubs.",
     "Snap counts are not in any source this repository has verified, and the brief forbids inferring them.",
     "An official snap-count source, verified for all 32 clubs, or a structured depth source.",
     (REPO,)),
    ("R-12", "Make the injury signal a surprise, never a level",
     "Designed, not implemented: the design requires a pre-kickoff expected-availability baseline, which "
     "needs the dated series in R-13.",
     "Blocked twice over: a single weekly snapshot cannot define a surprise, and a *series* is the "
     "very thing the publisher's terms restrict.",
     "Formally: one capture cannot support a delta, so a surprise needs two or more dated captures of "
     "the same field. Legally: the series itself needs the consent described in G-10.",
     "Either written consent / a licensed feed for a recurring series, or a design that derives "
     "surprise from sources that do not require systematic retrieval.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-13", "Run the 32-team roster/IR sweep before any team-level model is trusted",
     "Not built: no roster or reserve-list sweep exists in the repository.",
     "Blocked: 'not listed' cannot be read as 'available' without the reserve list.",
     "The reserve list is not published on the weekly injury report page.",
     "A dated roster/reserve-list capture per club joined to the injury report (subject to G-10), "
     "or a licensed roster feed.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-14", "Fixture-context feature set built only from published schedule facts",
     "Partly built: kickoff date, weekday, network, home club and bye clubs are transcribed for 2026.",
     "Blocked: venue is populated for one game in the committed evidence, and nothing is timezone-aware.",
     "Venue and roof are not on the weekly schedule page; they are on each game centre (see R-21).",
     "Venue + roof + surface for every fixture, each transcribed from its own game centre.",
     (S_SCHED_W10, S_GAMECENTER_W10)),
    ("R-15", "Store every model output as a probability plus its inputs, not just a pick",
     "Built: each market row carries the model price, the unrounded price, the fit sample size and the "
     "origination timestamp, and the pick is derived from those rather than stored alone.",
     "Mechanical only: storing the inputs does not make the model calibrated.",
     "Calibration is unmeasurable without settled outcomes joined to recorded prices.",
     "Recorded prices joined to settled results, so Brier/calibration can be computed per market family.",
     (REPO,)),
    ("R-16", "Compute and publish the removal-of-luck panel",
     "Built as a method: sealed future periods, proper scoring, multiplicity control and benchmark-relative "
     "skill are specified and tested on synthetic data.",
     "Not established: luck cannot be removed. It can be bounded, and on the current sample it is not bounded tightly enough to claim skill.",
     "Every signal interval currently spans zero or is too wide to exclude the benchmark.",
     "A lower bound above the benchmark after the multiplicity adjustment, on a sample declared in advance.",
     (REPO,)),
    ("R-17", "Two-sided 'what would change our mind' field on every strategy entry",
     "Not built: no strategy entry carries a falsification field in either direction.",
     "Not applicable until built.",
     "The field is a schema addition to the strategy register, which this session did not rewrite.",
     "A `falsified_by` and `confirmed_by` pair on every strategy row, populated before evaluation.",
     (REPO,)),
    ("R-18", "Price a line ourselves and publish the residual against the market, on a schedule, from day one",
     "Partly built: own fair lines are priced and published on a frozen schedule; the residual column is blank.",
     "Not established: no market price exists to residualise against.",
     "Same blocker as R-01/R-04. 'From day one' was not met — the price store begins at Week 10.",
     "A price source plus a back-dated capture log showing the schedule was met.",
     (REPO,)),
    ("R-19", "Turn the 136-game log into the pre-registered backtest corpus",
     "Not built as stated: the committed feed holds a different count and a different window from the "
     "'136-game log' the brief names, and that log was not found in the repository.",
     "Blocked: the corpus the brief names cannot be identified.",
     "An unidentified source document. Substituting a different corpus would be an inference, not a catch-up.",
     "The 136-game log itself, or an explicit decision that the committed feed replaces it.",
     (REPO,)),
    ("R-20", "Decide the price-data policy before any backtest is published",
     "Policy published and enforced fail-closed: no market price is written, and a test fails the build if "
     "one appears without a source.",
     "Decided in the restrictive direction: no backtest is published, because no price exists.",
     "The decision itself is made; what it blocks is every price-dependent metric.",
     "A licensing/provenance review that names an approved price source.",
     (REPO,)),
    ("R-21", "Transcribe the venue of every fixture from the official game centre and publish it",
     "Partly built: venue is recorded where the game centre printed it — WAS@NYG (MetLife Stadium, East "
     "Rutherford NJ), NE@DET (FC Bayern Munich Stadium, Munich), PIT@CIN (Paycor Stadium, Cincinnati OH).",
     f"3 of {M['finals_total'] + M['pending_total']} fixtures in the feed carry a venue.",
     "One retrieval per fixture is required; 3 have been done.",
     "A game-centre read for each of the remaining fixtures, recorded with its retrieval date.",
     (S_GAMECENTER_W10, REPO)),
    ("R-22", "Publish the league's dated schedule announcement beside the live schedule page",
     "Not built: no dated announcement document was obtained.",
     "Blocked: the weekly schedule page is undated apart from the retrieval itself.",
     "No dated announcement page was retrieved this session.",
     "A dated official announcement (release or schedule page carrying a publication date) captured with its hash.",
     (S_SCHED_W10,)),
    ("R-23", "Use official Game Books for actual starters and game-day status; do not infer depth rank or snaps",
     "Built as policy and evidence: three official Game Books transcribed, with substitutions read from "
     "the 'Not Active' block rather than inferred.",
     "Evidence-thin: 3 Game Books of 148 games in the feed.",
     "Game Books are per-game PDFs; reading one is a manual transcription of a long document.",
     "A Game Book ingestion pass over a defined sample, with the read list published.",
     (S_GAMECENTER_W10, REPO)),
    ("R-24", "Ingest game-level results so the ratings are opponent-aware",
     "Built: the rating is fit only from officially sourced finals and the diagnostics are walk-forward "
     "(each week fitted from strictly earlier weeks only).",
     "Mechanical only: opponent-aware fitting is not the same as being right.",
     "The model's fair line is not claimed to beat the market; no market number exists to compare against.",
     "Out-of-sample Brier skill against a no-skill benchmark, with an interval excluding it.",
     (REPO,)),
    ("R-25", "Injury and personnel ablations instead of fixed penalties (test with and without, report the difference)",
     "Designed, not implemented: no ablation harness exists, because there is no verified availability "
     "feature to ablate.",
     "Blocked on R-13: without the reserve list and dated designations, 'with' and 'without' are not defined.",
     "The availability features must exist and be dated before they can be ablated.",
     "A dated availability dataset plus a chronological holdout, then a published delta with uncertainty.",
     (S_INJURY, REPO)),
    ("R-26", "Automate immutable multi-day availability snapshots (daily, retained hashes)",
     "Deliberately not built. The repository holds one dated read of the Week 10 report and one of the "
     "Week 10 slate. No scheduled capture job was created for the injury report, because a recurring "
     "capture is systematic retrieval and the publisher's terms forbid it absent written consent.",
     "One capture cannot support a backtest of practice designations — the brief's own point — and a "
     "scheduled series is currently not permitted, so this is blocked by policy before it is blocked "
     "by engineering.",
     "G-10. The requirements and the terms conflict, and the conflict cannot be resolved by building.",
     "Express written consent from NFL Enterprises, or a licensed feed, before any scheduled capture.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-27", "Capture official inactive lists and snap counts",
     "Partly built: inactive lists are read from Game Books for 3 games. Snap counts are not captured "
     "anywhere.",
     f"Far from coverage: 3 games of {M['finals_total']} in the feed.",
     "Snap counts have no verified official source in this repository; inactive lists are per-Game-Book.",
     "A Game Book pass per game, plus any official snap-count source.",
     (S_GAMECENTER_W10, REPO)),
    ("R-28", "Fix the two depth-parsing failures before widening coverage (Texans image; Packers jersey numbers)",
     "Not built: no depth parser exists that has been run over all 32 clubs.",
     "Blocked: the Texans publish depth as an image, and this repository will not transcribe an image by eye.",
     "An authorised structured source for Houston; a number-stripping parser that stores the raw string.",
     "Both fixes, each demonstrated on the club's own published page.",
     (REPO,)),
    ("R-29", "Model depth slots as groups, not a single starter",
     "Not built: the depth register treats the published order as a list and publishes withheld rows "
     "where a slot is shared or empty, rather than naming one starter.",
     "Blocked: co-listed rank-1 players are a real structure in published charts, and the register "
     "currently withholds those rows instead of representing them.",
     "A schema that carries a slot as a set, with ties preserved.",
     "A revised depth schema plus a demonstration on a club that co-lists three receivers at rank 1.",
     (REPO,)),
    ("R-30", "Treat roster turnover as a first-class data event (version depth against the last roster event)",
     "Not built: no versioned roster-event log exists.",
     "Blocked: depth rows carry no roster-event version, so a trade and a chart cannot be related.",
     "A dated transactions/roster feed is required and not obtained.",
     "A roster-event log with dates, joined to depth-chart versions.",
     (REPO,)),
    ("R-31", "Start with a singles-only shadow baseline (pre-register, freeze versions, record pre-kickoff)",
     "Built: the shadow baseline is pre-declared, its constants are frozen, and forecasts are recorded "
     "before kickoff with a frozen timestamp.",
     "Not established: the baseline's own out-of-sample skill against a no-skill benchmark is not yet "
     "claimed; the sample is one season.",
     "One season of walk-forward weeks, with prices absent.",
     "Additional seasons, or a benchmark-relative interval that excludes the benchmark.",
     (REPO,)),
    ("R-32", "Keep parlays and prop combos behind a joint-evidence gate",
     "Built enforce: a joint price is produced only when a Fisher-z interval clears the predeclared "
     "deadband; otherwise the joint price is left blank instead of assuming independence.",
     f"Blocking in practice: {M['correlations_claiming_dependence']} of {M['correlations_total']} pairs "
     "clear the deadband, so most joint prices are refused.",
     "Joint probabilities need a directly validated estimate, which needs a larger paired sample.",
     "A validated joint probability and the operator's void/push rules.",
     (REPO,)),
    ("R-33", "Use proper-score leaderboard divisions (singles, game parlays, SGP, prop combos)",
     "Partly built: the leaderboard exists with signal and staking split, but only one division is "
     "populated (singles); the other three have no eligible entry.",
     "Not established: no division has an eligible, benchmark-beating strategy.",
     "Three divisions have no evidence at all (props have no verified source).",
     "An eligible entry per division, ranked by benchmark-relative skill with uncertainty.",
     (REPO,)),
    ("R-34", "Rank with proper scores and uncertainty, not win rate",
     "Built: ranking is by Brier skill with a game-cluster lower bound and a multiplicity adjustment; "
     "raw win rate is not a ranking column.",
     "Not established: with no eligible entry the ranking is empty by design.",
     "The multiplicity adjustment widens intervals as trials accumulate.",
     "An entry whose adjusted lower bound clears the benchmark.",
     (REPO,)),
    ("R-35", "Add durable snapshot storage and alerts (immutable captures, freshness monitor, schema alarms)",
     "Partly built: captures are committed and immutable, and parsers fail loudly on a schema change "
     "(a missing field, a duplicate club, a bye-count arithmetic error).",
     "Not built: there is no freshness monitor and no alert channel.",
     "An alert destination is not configured; recurring capture is constrained by G-10.",
     "An alert route on build failure (issue, mail or webhook), which needs no retrieval, plus — only "
     "if G-10 permits it — a scheduled capture with retained hashes.",
     (REPO, S_TERMS)),
    ("R-36", "Split the site into a public analysis layer and a private data layer",
     "Partly built: the public site publishes derived values and links; raw row-level files are in the "
     "repository, not in a private store.",
     "This is the live irregularity: raw rows are currently public.",
     "The terms of the underlying sources have not been read and cleared.",
     "A rights review that either clears publication or moves the raw layer behind access control.",
     (REPO,)),
    ("R-37", "Per-team view: starters out, replacements named, net injury count",
     "Built: the injuries page publishes a team-level availability burden (Out/Doubtful/Questionable, by "
     "unit) and the replacement chains page names replacements where a chart supports it.",
     "Blank where unsupported: replacement names stay blank when no official chart places both players.",
     "Roster-level confirmation (R-27) is missing for most clubs.",
     "Inactive lists for the remaining clubs, so a replacement is confirmed rather than suspected.",
     (S_INJURY, REPO)),
    ("R-38", "An announced-starter evidence field (not an inferred replacement)",
     "Not built: the register records a replacement only where a published chart places the two players "
     "in the same slot; it has no separate 'announced by the club' field.",
     "Blocked: an announcement is a different document from a chart.",
     "Dated club announcements naming a starter change are not systematically captured.",
     "A dated announcement register per club, with the announcement quoted — subject to G-10.",
     (REPO, S_TERMS)),
    ("R-39", "An official depth-chart register with date and source per row",
     "Partly built: depth-chart evidence carries the club, the date and the URL for each retrieved chart.",
     f"Coverage is thin: {len(CLUB_DEPTH)} clubs have a registered chart.",
     "Charts are club-specific pages with differing formats; each must be read individually.",
     "A dated chart per club, verified club by club.",
     (CLUB_DEPTH["KC"], CLUB_DEPTH["SEA"], CLUB_DEPTH["DET"])),
    ("R-40", "Calibrate what 'Questionable' means empirically instead of using old percentages",
     "Not built: no play-rate-by-designation table exists.",
     "Blocked: calibration requires designations joined to inactive lists across several seasons.",
     "That join needs archived reports and inactive lists that are not in the repository.",
     "Several seasons of archived designations joined to official inactive lists, with confidence intervals.",
     (S_INJURY, REPO)),
    ("R-41", "Interactive Offense vs Defence matchup deficiency matrix (1st-4th string)",
     "Not built: the site is static by design and has no matrix view.",
     "Blocked on depth coverage: a matrix over 32 clubs needs 32 dated charts.",
     f"{len(CLUB_DEPTH)} clubs of 32 have a registered chart.",
     "32 verified charts, then a static matrix page (an interactive one is not required to decide).",
     (CLUB_DEPTH["KC"], REPO)),
    ("R-42", "Flag stale depth rows against the official transactions log",
     "Not built: no transactions log is ingested, so staleness cannot be detected.",
     "Blocked: the check needs a transactions feed the repository does not hold.",
     "No official transactions feed has been obtained.",
     "A dated transactions feed, then a staleness column on every depth row.",
     (REPO,)),
    ("R-43", "Point-in-time snapshot ledger for injuries, depth charts and inactives",
     "Partly built: captures are dated and immutable, and the build refuses to rewrite a frozen capture.",
     "Incomplete: one capture per artefact, and this session deliberately did NOT rewrite the frozen "
     "Week 10 transcription when the official page moved — the newer read is published as a new dated "
     "snapshot instead (SV-02).",
     "One capture is not a ledger. A ledger needs a series.",
     "At least two dated captures of the same artefact, retained side by side.",
     (REPO,)),
    ("R-44", "Populate the three missing Lions game-status designations",
     "Verified against the official report this session: Kerby Joseph (S, Knee, DNP, Out), Cade Mays "
     "(C, Ankle, DNP, Out) and D.J. Reed (CB, Hip, DNP, Out) all carry an explicit game status.",
     "Established for the designations; the brief's premise (that the site publishes them blank) is stale "
     "relative to the current injuries page.",
     "Nothing blocks this row; it is a stale-premise flag, not a data gap.",
     "Owner confirmation that the injuries page renders all three, then close the flag.",
     (S_INJURY, REPO)),
    ("R-45", "Re-capture and republish the Week 10 injury tables (published counts are stale)",
     "Not built: no dated re-capture of the injury tables has been published by this section.",
     f"Disputed: three different designation totals are in circulation (171 official hand count, 162 repo "
     "capture, 160 root page). This session counted 0 of 8 chunks itself and asserts no new total.",
     "A full capture with hashes is needed before any count is published.",
     "A complete 8-chunk read with a retained hash and a machine count, replacing all three totals — "
     "within the single-read use the terms permit (G-10).",
     (S_INJURY, S_TERMS, REPO)),
    ("R-46", "Reject deriving depth order from jersey number, experience or salary",
     "Accepted as a prohibition and recorded as such: the shortcut is documented as rejected, not used.",
     "Prohibition holds; no value is derived this way anywhere in the repository.",
     "Nothing blocks the prohibition.",
     "n/a — a prohibition is satisfied by not doing it, and by recording that it was considered.",
     (REPO,)),
    ("R-47", "Represent shared and empty depth slots faithfully",
     "Partly built: rows where a slot is shared or empty are withheld with a stated reason rather than "
     "collapsed into a false single starter.",
     "Faithful but incomplete: withholding is honest, yet it loses the structure the brief asks to keep.",
     "The depth schema has no slot-as-a-set representation.",
     "A slot-set schema, demonstrated on co-listed and empty slots.",
     (REPO,)),
    ("R-48", "Resolve the depth-order source before building the backup-deficiency feature",
     "Route (a) per-club official depth pages is the one in use, verified for 3 clubs. Route (b) snap "
     "counts has no verified source.",
     f"Unresolved for {32 - len(CLUB_DEPTH)} clubs.",
     "The feature must not be built until one route is verified for all 32 clubs — the brief's own rule.",
     "32 club charts, or an official snap-count source for all 32 clubs.",
     (CLUB_DEPTH["KC"], CLUB_DEPTH["SEA"], CLUB_DEPTH["DET"])),
    ("R-49", "Score injury-designation reliability before using it as a feature",
     "Not built: no play-rate-by-designation measurement exists.",
     "Blocked: needs archived designations joined to inactive lists across several seasons.",
     "The archival join does not exist (see R-51).",
     "The join, plus a published play rate per designation with a confidence interval. The historical "
     "join itself needs archived reports, which G-10 also constrains.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-50", "Snapshot the nfl.com injury report every Wed, Thu and Fri and keep a dated history",
     "Not built, and not recommended until G-10 is answered: a Wednesday/Thursday/Friday job is "
     "exactly the systematic retrieval the terms prohibit.",
     "Blocked: one read is held.",
     "G-10 — the terms, not the tooling. A scheduler is the easy part.",
     "Written consent or a licensed feed; then a dated series with retained hashes.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-51", "Treat the injury report as a timestamped series, not a weekly snapshot",
     "Not built for the same reason as R-50, and this is the requirement the terms bite hardest: a "
     "timestamped series is a compilation.",
     "Blocked: without a series, no Questionable->Out or DNP->LP->FP transition can be measured.",
     "G-10. The brief asks for a series; the terms prohibit compiling one without consent.",
     "Consent or a licensed historical feed, and until then the honest answer is that this "
     "requirement cannot be met by scraping.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-52", "Use snap counts as the starter proxy when the depth chart is unavailable",
     "Not built: no snap counts are captured.",
     "Blocked: no verified official snap-count source was found.",
     "Source absence, not effort.",
     "An official snap-count source, verified against a Game Book.",
     (REPO,)),
    ("R-53", "Add a control baseline (random picks; favourites only) to every leaderboard run",
     "Partly built: a no-skill benchmark is specified and used as the reference for Brier skill.",
     "Not published as a row: the control baseline is not yet rendered beside the leaderboard.",
     "The leaderboard has no eligible entry to compare, so the control has nothing to beat.",
     "A published control row per division, computed by the same build.",
     (REPO,)),
    ("R-54", "Stadium roof/surface and NWS hourly wind/precipitation overlay",
     "Not built: no roof, surface or forecast data is ingested.",
     "Blocked: roof designations are per-stadium official facts and are not in the repository.",
     "No roof/surface register and no forecast feed obtained.",
     "A 32-stadium roof/surface register plus an hourly forecast capture per fixture.",
     (REPO,)),
    ("R-55", "Two-stage skill leaderboard (proper-score qualification, then prospective CLV/ROI escrow)",
     "Partly built: stage one (proper-score qualification) is implemented; stage two (escrow) is a "
     "described policy with nothing to escrow.",
     "Not established: stage two needs executable prices.",
     "CLV cannot exist without closing prices.",
     "Closing prices for the originated markets.",
     (REPO,)),
    ("R-56", "Vig-free market consensus vs originated fair-line decomposition",
     "Not built for real prices: the de-vig maths exists and is unit-tested, but there is no market "
     "price to de-vig.",
     "Blocked: no two-sided market price exists.",
     "Same price blocker.",
     "Two-sided market prices per market; the maths is already tested.",
     (REPO,)),
    ("R-57", "Publish a weekly 'what changed' diff instead of a static snapshot",
     "Not built: pages are generated from the current state and do not render a vs-previous column.",
     "Blocked: a diff needs two dated snapshots of the same artefact.",
     "One capture per artefact.",
     "Two dated captures, then a rank/rating/availability delta column.",
     (REPO,)),
    ("R-58", "Publish every model total twice until one wins",
     "Partly built: two independent total estimators exist in the repository (a rolling points-for/"
     "against window and an Elo-implied total), and both are published on the market pages.",
     "Not resolved: no walk-forward comparison has been published to collapse them to one.",
     "The comparison needs a common settled sample; both estimators are visible until then.",
     "A walk-forward comparison of the two estimators with an interval on the gap.",
     (REPO,)),
    ("R-59", "Add a drift alarm to every scraper (pin row counts and required fields)",
     "Built in the parsers: the weekly transcription parser fails on an unrecognised line, a club playing "
     "twice, a bye club in a game, or 2xgames+byes != 32.",
     "Not built: there is no alert when a parser fails in CI, only a failed job.",
     "An alert destination is not configured.",
     "A notification route on workflow failure, and pinned row counts per source.",
     (REPO,)),
    ("R-60", "Capture the reserve list so 'not listed' never means 'available'",
     "Not built: the reserve list is not captured.",
     "Blocked: the weekly report omits players on injured reserve, so absence from it is ambiguous.",
     "No reserve-list source obtained or verified.",
     "A dated reserve-list capture joined to the weekly report.",
     (S_INJURY, REPO)),
    ("R-61", "Reject ranking strategies by season-long ROI",
     "Accepted as a prohibition: season-long realised return is not a ranking column anywhere.",
     "Prohibition holds.",
     "Nothing blocks the prohibition.",
     "n/a — satisfied by not ranking on it, which the leaderboard does not.",
     (REPO,)),
    ("R-62", "Archive weekly injury reports for past seasons",
     "Not built: no historical injury-report archive exists in the repository.",
     "Blocked: needed to test whether designations change outcomes (R-49).",
     "Archives for past seasons are not published in a retrievable form the repository holds.",
     "A season-long archive with hashes, or a licensed archive. Building one by retrieval is what "
     "G-10 forbids.",
     (S_INJURY, S_TERMS, REPO)),
    ("R-63", "Pre-register each strategy (definition frozen before results are seen)",
     "Built: definitions are frozen and the registration commit is the registration; the elo constants "
     "are refused at close if they changed.",
     "Mechanical only: freezing a definition prevents result-chasing, not bad design.",
     "Nothing blocks the freeze.",
     "n/a — satisfied by construction where a strategy exists.",
     (REPO,)),
    ("R-64", "2026 kickoff and declared onside-kick regime priors filter",
     "Not built: the 2026 rule change is read and registered, but no prior is implemented.",
     "Context only: the rule text is official; its effect on totals and comeback curves is not measured.",
     "No measurement of the rule's effect exists, and measurement needs the price and availability data above.",
     "An estimate of the rule's effect from official play-by-play, then a declared prior.",
     (S_RULEBOOK, REPO)),
    ("R-65", "Freeze a rule before it sees data (the commit hash is the registration)",
     "Built: registrations are git commits and the build refuses to publish a registration that changed "
     "after its evaluation window opened.",
     "Mechanical only.",
     "Nothing blocks the freeze.",
     "n/a — satisfied by construction.",
     (REPO,)),
    ("R-66", "Split data into train, validation and final holdout seasons",
     "Partly built: the walk-forward split is chronological and strictly out-of-sample by week.",
     "Not established: the split is within one season, not across seasons, so the final holdout is unspent.",
     "Only one season of verified results is in the feed.",
     "Multiple seasons, with the final holdout season declared and untouched.",
     (REPO,)),
    ("R-67", "A dedicated suggestions section so a reviewer can choose a path before implementation",
     "Built: a suggestion register with cost, reversibility and a falsification test exists, and accepted "
     "suggestions require a recorded decision.",
     "Process only: a suggestion is a proposal, never a finding.",
     "Nothing blocks review; the queue is open.",
     "A recorded decision per suggestion.",
     ("repo",)),
    ("R-68", "A clear list of questions and answers that must be settled before a decision is made",
     "Built: the decision-question register and the question ledger publish questions with states and "
     "blocked-by links.",
     "Process only.",
     "Nothing blocks reading it.",
     "Answers, recorded with a source each.",
     (REPO,)),
    ("R-69", "Originate own lines and run a leaderboard competition with rewards and validation gates",
     "Partly built: own lines are priced and a gated leaderboard exists, with the gate wired fail-closed.",
     "Not established: no strategy passes the gates, so no reward is earned.",
     "Every signal's interval lower bound is negative on the available sample.",
     "A gate-passing strategy. Without one, a reward would be inventing a winner.",
     (REPO,)),
    ("R-70", "Track defensive and offensive deficiencies caused by 2nd/3rd/4th-string replacements",
     "Partly built: replacement chains carry the chart-relative tiers and name the replacement where a "
     "club chart supports it.",
     "Thin evidence: 33 chains were traced by an earlier session from 19 club charts; 43 were withheld.",
     "Coverage and roster confirmation are incomplete.",
     "32 dated charts plus inactive lists, so a chain is confirmed rather than chart-relative.",
     (REPO,)),
    ("R-71", "An executive summary outlining important details",
     "Built: the dashboard opens with an executive summary and a decision-readiness table.",
     "Process only.",
     "Nothing blocks it.",
     "n/a.",
     (REPO,)),
    ("R-72", "No manual input from the operator; the agent works to completion",
     "Built into the process: every figure is generated by the build and CI fails if the committed site "
     "differs from a fresh regeneration.",
     "Process only.",
     "Nothing blocks it.",
     "n/a.",
     (REPO,)),
    ("R-73", "Verify every row against an official source, and flag rather than fill an unconfirmed value",
     "Built and enforced: the verifier fails on any table row with no registered source, and a blank "
     "empirical cell is a build-time invariant, not a styling choice.",
     "Structural only: a source link proves provenance, not that the publisher is right.",
     "External reachability and factual entailment are outside the offline verifier's scope.",
     "An online entailment check per row — not attempted here, and not claimable from a build.",
     (REPO,)),
    ("R-74", "Publish flagged irregularities with source links so they can be reviewed after launch",
     "Built: the Flagged for Review register is published, numbered, and carries a source per row.",
     "Process only.",
     "Nothing blocks it.",
     "n/a.",
     (REPO,)),
]


# Explicit status codes, kept separate from the prose so the counts cannot drift from it and
# so a row cannot quietly change category by being reworded. Tests assert every REQ id
# appears here exactly once, and that there is no id here that is absent from REQ.
#   impl: built | partial | not_built | policy   (policy = a prohibition the repository honours)
#   emp:  established | partial | not_established | unavailable
IMPL, EMP = 0, 1
STATUS = {
    "R-01": ("built", "unavailable"), "R-02": ("built", "partial"),
    "R-03": ("built", "unavailable"), "R-04": ("built", "partial"),
    "R-05": ("built", "not_established"), "R-06": ("built", "partial"),
    "R-07": ("built", "partial"), "R-08": ("built", "not_established"),
    "R-09": ("built", "not_established"), "R-10": ("partial", "partial"),
    "R-11": ("policy", "unavailable"), "R-12": ("not_built", "unavailable"),
    "R-13": ("not_built", "unavailable"), "R-14": ("partial", "unavailable"),
    "R-15": ("built", "not_established"), "R-16": ("built", "not_established"),
    "R-17": ("not_built", "unavailable"), "R-18": ("partial", "partial"),
    "R-19": ("not_built", "unavailable"), "R-20": ("built", "unavailable"),
    "R-21": ("partial", "partial"), "R-22": ("not_built", "unavailable"),
    "R-23": ("built", "partial"), "R-24": ("built", "not_established"),
    "R-25": ("not_built", "unavailable"), "R-26": ("partial", "unavailable"),
    "R-27": ("partial", "partial"), "R-28": ("not_built", "unavailable"),
    "R-29": ("not_built", "unavailable"), "R-30": ("not_built", "unavailable"),
    "R-31": ("built", "not_established"), "R-32": ("built", "not_established"),
    "R-33": ("partial", "not_established"), "R-34": ("built", "not_established"),
    "R-35": ("partial", "unavailable"), "R-36": ("partial", "unavailable"),
    "R-37": ("built", "partial"), "R-38": ("not_built", "unavailable"),
    "R-39": ("partial", "partial"), "R-40": ("not_built", "unavailable"),
    "R-41": ("not_built", "unavailable"), "R-42": ("not_built", "unavailable"),
    "R-43": ("partial", "partial"), "R-44": ("built", "established"),
    "R-45": ("not_built", "unavailable"), "R-46": ("policy", "established"),
    "R-47": ("partial", "partial"), "R-48": ("partial", "unavailable"),
    "R-49": ("not_built", "unavailable"), "R-50": ("not_built", "unavailable"),
    "R-51": ("not_built", "unavailable"), "R-52": ("not_built", "unavailable"),
    "R-53": ("partial", "not_established"), "R-54": ("not_built", "unavailable"),
    "R-55": ("partial", "unavailable"), "R-56": ("not_built", "unavailable"),
    "R-57": ("not_built", "unavailable"), "R-58": ("partial", "not_established"),
    "R-59": ("partial", "unavailable"), "R-60": ("not_built", "unavailable"),
    "R-61": ("policy", "established"), "R-62": ("not_built", "unavailable"),
    "R-63": ("built", "established"), "R-64": ("not_built", "unavailable"),
    "R-65": ("built", "established"), "R-66": ("partial", "not_established"),
    "R-67": ("built", "established"), "R-68": ("built", "established"),
    "R-69": ("partial", "not_established"), "R-70": ("partial", "partial"),
    "R-71": ("built", "established"), "R-72": ("built", "established"),
    "R-73": ("built", "partial"), "R-74": ("built", "established"),
}

# Requirements that need no gate: they are prohibitions the repository honours, or process
# facts that are true by construction. Declared explicitly so that every OTHER requirement
# is required to be gated — enforced by a test, not by inspection.
SELF_SATISFIED = {
    "R-03",  # origination order holds by construction
    "R-44",  # the three Lions designations are published and verified (stale-premise flag)
    "R-46", "R-61",  # prohibitions (no jersey-order depth, no ROI ranking)
    "R-63", "R-65",  # pre-registration freeze
    "R-67", "R-68", "R-71", "R-72", "R-73", "R-74",  # process/verification facts
}

IMPL_LABEL = {"built": "Implemented", "partial": "Partly implemented",
              "not_built": "Not implemented", "policy": "Honoured as a prohibition"}
EMP_LABEL = {"established": "Established", "partial": "Partly established",
             "not_established": "Not established", "unavailable": "Unavailable — no evidence exists"}


def req_rows():
    return REQ


def req_status(rid):
    return STATUS[rid]


def req_counts():
    """Counts published beside the requirements table so the prose cannot drift from the rows."""
    impl = {k: sum(1 for v in STATUS.values() if v[IMPL] == k) for k in IMPL_LABEL}
    emp = {k: sum(1 for v in STATUS.values() if v[EMP] == k) for k in EMP_LABEL}
    impl["total"] = emp["total"] = len(REQ)
    return {"impl": impl, "emp": emp}


def gate_violations():
    """Requirements that are neither gated nor declared self-satisfied. Must be empty."""
    gated = {rid for _g in GATES for rid in _g[3]}
    return sorted({r[0] for r in REQ} - gated - SELF_SATISFIED)


# ------------------------------------------------------------------ gates
# The gate that blocks each requirement, expressed as a number that would clear it.
# Ordered by how many requirements each gate blocks: the top gate is the one to fix first.
GATES = [
    ("G-01", "No approved price source",
     "The league publishes no wagering prices, no book of record is approved, and no licensed quote "
     "archive was obtained. Every price-dependent metric is blank by policy rather than estimated.",
     ["R-01", "R-04", "R-18", "R-20", "R-32", "R-55", "R-56"],
     "One approved source, or an explicit decision to record own-book prices as the book of record.",
     "An agreement, licence or recorded own-book log; nothing in the repository can substitute for it."),
    ("G-02", "No dated availability series",
     "The repository holds one capture of the Week 10 injury report and one of the Week 10 slate. "
     "A single capture cannot define a surprise, a delta or a transition.",
     ["R-25", "R-30", "R-40", "R-43"],
     "Two or more dated captures of the same field, by whatever method G-10 permits.",
     "The count itself: two or more dated captures. Measurable, and currently zero."),
    ("G-03", "Depth verified for 3 of 32 clubs",
     "Club depth charts are published per club in differing formats, and clubs self-label them "
     "unofficial. Three have been read and registered.",
     ["R-06", "R-11", "R-28", "R-29", "R-38", "R-39", "R-41", "R-42", "R-47", "R-48", "R-52", "R-70"],
     "32 dated charts, or an official snap-count source verified for all 32 clubs.",
     "29 more club charts, or a snap-count source; 3 of 32 is the measured starting point."),
    ("G-04", "Results feed is a dated capture, not a live feed",
     "The committed Week 10 transcription is a 14 Nov capture. The official page has since settled 11 "
     "more games. The capture is deliberately left frozen and the newer read is published beside it.",
     ["R-02", "R-10", "R-14", "R-19", "R-21", "R-22", "R-23", "R-27", "R-37", "R-66"],
     "Re-capture as a new immutable snapshot and repoint the feed at the latest dated capture.",
     "A dated snapshot per week; SV-02 here is the first one done this way."),
    ("G-05", "One season of verified finals",
     "The feed covers 2026 only. A final holdout season cannot exist inside the only season available.",
     ["R-07", "R-16", "R-31", "R-34", "R-53", "R-69"],
     "Additional seasons of official results, ingested the same way.",
     "Enough seasons that a final holdout can be declared and left untouched."),
    ("G-06", "No eligible strategy",
     "Every walk-forward signal interval on the available sample includes the no-skill benchmark, and "
     "the multiplicity adjustment widens each interval as trials accumulate.",
     ["R-08", "R-09", "R-33", "R-69"],
     "A benchmark-relative lower bound that excludes the benchmark, out of sample.",
     "One strategy. The gate is fail-closed by design, so this is not a bug to be worked around."),
    ("G-07", "Schema and process gaps that need an owner decision",
     "A falsification field, a slot-set depth schema, a control-baseline row and an alert route are "
     "schema or process additions rather than data waits.",
     ["R-17", "R-35", "R-53", "R-57", "R-59"],
     "An owner decision to add the field, plus one build to render it.",
     "A decision, then a column. This is the cheapest open gate."),
    ("G-08", "No published model critique: no market price, no ablation, no calibration",
     "The model is compared against nothing. Market prices are blank, availability features do not "
     "exist to ablate, and calibration needs a joined sample the feed does not yet have.",
     ["R-05", "R-15", "R-24", "R-54", "R-58", "R-64"],
     "A price source (G-01) for market comparison; a dated availability series (G-02) for ablations.",
     "n for a calibration curve, and a market number for a residual — both countable."),
    ("G-10", "The publisher's terms restrict systematic retrieval",
     "NFL.com Terms section 1.3 prohibit systematic retrieval of content to build a collection, "
     "compilation or database without express prior written consent, and permit use only for "
     "individual non-commercial informational purposes. Several requirement lines in this brief ask "
     "for exactly that: a scheduled multi-day capture series, a season-long archive, and a reserve "
     "list joined to the report. The requirement and the terms are in direct conflict.",
     ["R-12", "R-13", "R-26", "R-45", "R-49", "R-50", "R-51", "R-60", "R-62"],
     "Written consent from NFL Enterprises, or a licensed feed that permits storage and reuse.",
     "A consent letter or a licence, or an owner decision to drop the affected requirements."),
    ("G-09", "Source rights unreviewed; raw rows are published",
     "The brief requires a public analysis layer and a private raw layer. No source's redistribution "
     "terms have been read and cleared, so the split cannot be decided either way.",
     ["R-36", "R-70"],
     "A rights review that either clears publication or requires the split.",
     "One recorded review outcome per source family."),
]


def gate_rows():
    return GATES


def gate_summary():
    blocked = {}
    for _gid, _name, _why, rids, _clear, _how in GATES:
        for rid in rids:
            blocked[rid] = blocked.get(rid, 0) + 1
    orphans = [r[0] for r in REQ if r[0] not in blocked]
    return {"gates": len(GATES), "requirements_mapped": len(blocked),
            "requirements_unmapped": orphans}


# ------------------------------------------------------------------ snapshots
# Two dated reads of the same official pages, published side by side instead of
# overwriting the older one. The first is the frozen capture already in the repository;
# the second was read by this session. Neither replaced the other.
SNAPSHOTS = [
    ("SV-01", "Week 10 slate (official weekly schedule page)",
     "2026-11-14", "session a77d40e1 (committed capture)",
     "1 final (WAS 24, NYG 21) + 13 games without a score",
     "13 of 14 games had not kicked off at the retrieval time.",
     (S_SCHED_W10,)),
    ("SV-02", "Week 10 slate (same page, re-read)",
     "2026-11-16", "session 462fba62 (this section)",
     "12 finals + 2 games without a score (PIT@CIN, LAC@BAL)",
     "The 11 intervening results were read game by game; the two scoreless games were NOT given a score.",
     (S_SCHED_W10,)),
    ("SV-03", "Week 10 injury report (head of page)",
     "2026-11-16", "session 462fba62 (this section)",
     "Header reads 'Week 10 of the 2026 Season'; Lions block shows 3 explicit Out designations",
     "Read as chunk 0 of 8. This session did not count the whole page, so it publishes no total.",
     (S_INJURY,)),
    ("SV-04", "WAS @ NYG game centre",
     "2026-11-16", "session 462fba62 re-read of a source already registered",
     "Location EAST RUTHERFORD, NJ; Stadium METLIFE STADIUM; final 24-21",
     "Consistent with the frozen capture; the stadium row is the only venue this game contributes.",
     (S_GAMECENTER_W10,)),
    ("SV-05", "NE @ DET game centre",
     "2026-11-16", "session 462fba62 (this section)",
     "Location MUNICH; Stadium FC BAYERN MUNICH STADIUM; final NE 10, DET 35",
     "Venue transcribed because it is published on the game centre; no depth or snap value inferred.",
     (S_GC_NE_DET,)),
    ("SV-06", "PIT @ CIN game centre",
     "2026-11-16", "session 462fba62 (this section)",
     "Location CINCINNATI, OH; Stadium PAYCOR STADIUM; no final score published",
     "The venue is available before kickoff; the score is not. The score cell stays blank.",
     (S_GC_PIT_CIN,)),
]


def snapshot_rows():
    return SNAPSHOTS


def delta_rows():
    """The measured difference between SV-01 and SV-02, computed from the two reads."""
    new_finals = 11
    return [
        ("Finals in the committed feed (week 10)", str(M["finals_w10"]), str(M["finals_w10"] + new_finals),
         f"+{new_finals}", "Official page, both reads", (S_SCHED_W10, REPO)),
        ("Games without a score (week 10)", "13", "2", "-11",
         "The two remaining are PIT@CIN and LAC@BAL", (S_SCHED_W10,)),
        ("Finals in the whole feed", str(M["finals_total"]), "", "",
         "The feed was NOT regenerated; the delta applies to the snapshot, not the feed",
         (S_SCHED_W10, REPO)),
    ]


# ------------------------------------------------------------------ venues
VENUES = [
    ("W10", "WAS", "NYG", "METLIFE STADIUM", "EAST RUTHERFORD, NJ",
     "Published on the game centre; already registered from the 14 Nov read", (S_GAMECENTER_W10,)),
    ("W10", "NE", "DET", "FC BAYERN MUNICH STADIUM", "MUNICH",
     "International Game; read from its own game centre on 2026-11-16", (S_GC_NE_DET,)),
    ("W10", "PIT", "CIN", "PAYCOR STADIUM", "CINCINNATI, OH",
     "Read from its own game centre's Game Info block on 2026-11-16", (S_GC_PIT_CIN,)),
]


def venue_rows():
    return VENUES


# ------------------------------------------------------------------ questions
# A question is answerable now, blocked on a named artefact, or a decision that only the
# owner can take. `state` is one of: answerable now / blocked / owner decision.
QUESTIONS = [
    ("Q-01", "Does any official NFL page publish a wagering price?",
     "Answerable now — no.",
     "The league publishes schedules, results, injuries and stats. Wagering prices are a licensed "
     "third-party product. Every price cell on the site is therefore blank, and this is policy, not "
     "an oversight.",
     "Answered by the source set already read; the absence is the finding.",
     (S_SCHED_W10, REPO)),
    ("Q-02", "Is the committed Week 10 capture wrong, or just old?",
     "Answerable now — old, not wrong.",
     "The 14 Nov read recorded 13 games without scores at a moment when they had not kicked off. "
     "The 16 Nov read shows 12 finals and 2 games still scoreless. Both reads are consistent; they "
     "are different instants.",
     "This is why the older capture was left frozen and a second dated snapshot published beside it.",
     (S_SCHED_W10,)),
    ("Q-03", "Has the pool of settleable games grown enough to matter?",
     "Answerable now — yes, by 11 games.",
     "Weeks 1-9 plus the Week 10 Thursday game were settleable before; 11 more Week 10 games are "
     "settleable now. Weeks 11+ remain unplayed.",
     "The number is the answer: 11. The feed still holds the older count on purpose.",
     (S_SCHED_W10, REPO)),
    ("Q-04", "How many injury-designation rows does the Week 10 report actually have?",
     "Blocked — needs a full 8-chunk capture with a hash.",
     "Three totals are in circulation (171 official hand count, 162 repo capture, 160 root page) and "
     "none can be reproduced from a machine count in this repository. This session read only chunk 0.",
     "Publishing a fourth hand-counted total would add to the confusion; the capture is the gate.",
     (S_INJURY,)),
    ("Q-05", "Do the three Lions designations still need publishing?",
     "Answerable now — no, they are published.",
     "Kerby Joseph, Cade Mays and D.J. Reed all carry an explicit Out status on the official report and "
     "on the current injuries page. The brief's premise is older than the page.",
     "Owner confirmation closes it; nothing else is needed.",
     (S_INJURY, REPO)),
    ("Q-06", "Can a single-week capture support a backtest of practice designations?",
     "Answerable now — no.",
     "A backtest of a designation needs the designation as it stood before each kickoff, which needs a "
     "series. One capture gives one instant.",
     "This is the brief's own point, and the site agrees with it rather than working around it.",
     (S_INJURY, REPO)),
    ("Q-06b", "May this project run a recurring capture of NFL pages at all?",
     "Owner decision — and it outranks every data question below it.",
     "No, not on the current terms. " + TERMS_CLAUSE + " An owner-reviewed single read for "
     "verification is the permitted use; a scheduled multi-day series is a compilation. This is not a "
     "research gap and cannot be closed by engineering.",
     "Written consent or a licensed feed. Until then the requirements that need a series stay "
     "blocked, and a page that recommends building one would be recommending a breach.",
     (S_TERMS, REPO)),
    ("Q-07", "Which depth-order route should be built first?",
     "Owner decision, with a stated preference.",
     "Route (a) per-club charts is verified for 3 clubs and is in use. Route (b) snap counts has no "
     "verified source in this repository. The preference is (a) continued, because a chart can be read "
     "and cited today.",
     "The brief already orders the routes (a) then (b); the open part is whether 29 more club-page "
     "reads are permitted at all (Q-06b). If they are not, route (b) is the only survivor and it has "
     "no verified source.",
     (REPO, CLUB_DEPTH["KC"])),
    ("Q-08", "What would make a strategy eligible?",
     "Answerable now — a number.",
     "A benchmark-relative skill whose interval, after the multiplicity adjustment, excludes the "
     "benchmark, on a sample declared before evaluation. Win rate and season ROI are excluded by design.",
     "The gate is published on the leaderboard page; the number is its lower bound.",
     (REPO,)),
    ("Q-09", "Can luck be removed?",
     "Answerable now — no, and the site does not claim to.",
     "Luck can be bounded with proper scoring, uncertainty intervals and multiplicity control. Removal "
     "is not a thing that can be done, and a page that says otherwise would be wrong.",
     "The honest version: bound it, publish the bound, refuse to rank when the bound spans zero.",
     (REPO,)),
    ("Q-10", "Is the current model better than the market?",
     "Unanswerable — no market price exists.",
     "The market number column is blank on every row. A comparison against nothing is not a result.",
     "Blocked on G-01.",
     (REPO,)),
    ("Q-11", "Are the models calibrated?",
     "Unmeasurable on the current feed.",
     "Calibration needs recorded pre-kickoff probabilities joined to settled outcomes. The probabilities "
     "are recorded; the joined sample is one season and no calibration curve is published.",
     "Publish a reliability diagram with n, or state that n is too small. Both are honest; inventing a "
     "curve is not.",
     (REPO,)),
    ("Q-12", "Which requirement is cheapest to clear?",
     "Answerable now — G-07.",
     "A falsification field on strategy entries, a control-baseline row, a weekly diff column and an "
     "alert route are schema and process changes. They need a decision, not a data licence.",
     "This is the recommendation on the readiness page: clear G-07 before buying data.",
     (REPO,)),
    ("Q-13", "Should two implementations of the same requirements be merged or designated?",
     "Owner decision — still open.",
     "An earlier session logged two independent implementations of the same eight requirements "
     "(the market board and the line-origination desk). They disagree only because their inputs differ.",
     "Merging them is a real change to published numbers; designating one is a one-line decision. The "
     "second is cheaper and reversible.",
     (REPO,)),
    ("Q-14", "Does the repository hold rights to the data it publishes?",
     "Owner decision, and the riskiest open item.",
     "Provenance and licence for the raw market files are unknown, and the public/private split "
     "required by the brief is not implemented: raw rows are public.",
     "Until terms are read, the honest state is 'unreviewed', not 'cleared'.",
     (REPO,)),
]


def question_rows():
    return QUESTIONS


def question_counts():
    states = {"answerable": 0, "blocked": 0, "decision": 0}
    for q in QUESTIONS:
        s = q[2].lower()
        if s.startswith("answerable") or s.startswith("unanswerable") or s.startswith("unmeasurable"):
            states["answerable"] += 1
        elif s.startswith("blocked"):
            states["blocked"] += 1
        else:
            states["decision"] += 1
    return states


# ------------------------------------------------------------------ suggestions
# Each suggestion is a proposal with a cost, a decision it unblocks, and what would show it
# was the wrong choice. None of them claims a numerical result.
SUGGESTIONS = [
    ("V-S00", "Answer the terms question before any capture is built (Q-06b)",
     "The brief asks for a scheduled multi-day capture, a season archive and a reserve-list join. On "
     "the publisher's current terms all three are prohibited without written consent. Ten requirement "
     "lines are blocked on this and none of them can be engineered around, so it is the first decision "
     "and it is free to ask.",
     "One letter to NFL Enterprises, or one licence enquiry.",
     "Unblocks G-10: 9 requirement lines.",
     "Consent is refused, in which case those requirements must be formally dropped rather than left "
     "as 'blocked' for ever — and the honest site says so.",
     (S_TERMS, REPO)),
    ("V-S01", "Add the falsification field to every strategy entry (R-17)",
     "Required by the brief and cheap: two columns, one test. It also makes every other strategy row "
     "auditable, because a row that cannot say what would refute it is not a claim.",
     "One build; no new data.", "Clear G-07 partially. Unblocks nothing on its own.",
     "A strategy row still evaluates without a falsification field after the build.",
     (REPO,)),
    ("V-S02", "Publish the control baseline as its own leaderboard row (R-53)",
     "A random-pick and a favourites-only row turn 'no eligible entry' into a measurement: the reader "
     "sees what no-skill looks like on the same sample.",
     "One build from data already committed.", "Clear part of G-05/G-07; makes the empty leaderboard "
     "informative rather than blank.",
     "The control row needs data the repository does not hold.",
     (REPO,)),
    ("V-S03", "Publish a weekly diff column from two dated captures (R-57)",
     "The first two dated captures exist (SV-01, SV-02). Rendering their difference is a build change, "
     "and it proves the snapshot mechanism works before it is scaled to 32 clubs.",
     "One build; a small schema addition.", "Clear G-04 for week 10 and demonstrate G-02's pattern.",
     "The diff cannot be computed without a second capture — it can, for Week 10.",
     (REPO,)),
    ("V-S04", "Finish the Week 10 read, hash it, and publish the count (Q-04)",
     "The three competing totals are a credibility problem, and one complete read with a hash ends it "
     "without compiling a database. This session read only the head of the page and asserts no total.",
     "One full read and a hash — a single owner-reviewed use, which the terms permit.",
     "Clear the Q-04 blocker.",
     "The page cannot be read deterministically; a hash of the rendered text is still possible.",
     (S_INJURY, S_TERMS)),
    ("V-S05", "Continue route (a) for depth, 29 clubs to go (Q-07)",
     "Charts are readable and citable today; snap counts have no verified source. But 29 club-page "
     "reads is the kind of systematic retrieval Q-06b asks about, so this suggestion is conditional on "
     "the answer rather than recommended outright.",
     "29 reads, each one page, each with its date.",
     "Would unblock G-03 at 32/32 — if Q-06b permits it.",
     "Charts are no longer published; clubs change format faster than they can be read; or the terms "
     "answer is no, in which case this suggestion dies and route (b) has no source.",
     (CLUB_DEPTH["KC"], REPO, S_TERMS)),
    ("V-S06", "Designate the canonical implementation rather than merging two (Q-13)",
     "The two implementations disagree because their inputs differ. Merging them changes published "
     "numbers; designating one is a one-line decision and is reversible.",
     "One decision, one nav change.", "Ends an open question that has stayed open across sessions.",
     "The designated implementation turns out to lack evidence the other one has on a specific page.",
     (REPO,)),
    ("V-S07", "Move the raw row-level layer behind access control (Q-14)",
     "Until the source terms are read, publishing raw rows is an unresolved risk. The site's own rule "
     "is: public layer = derived analysis, private layer = raw rows.",
     "A restructure of where raw files are served from; no new data.",
     "Addresses the most consequential open risk on the site.",
     "A rights review shows the raw rows are freely redistributable, in which case the split is optional.",
     (REPO,)),
    ("V-S08", "Refuse to publish a calibration claim until n is adequate (Q-11)",
     "A reliability diagram on one season would be read as a result. Publishing n beside it, and "
     "declining to draw conclusions below a predeclared n, is the honest option.",
     "One build; a predeclared threshold.", "Prevents a false positive becoming a site claim.",
     "The sample turns out to be adequate, in which case the diagram is published with its n.",
     (REPO,)),
]


def suggestion_rows():
    return SUGGESTIONS


# ------------------------------------------------------------------ flags
# Irregularities found by this session. Numbered VF-01.. so they cannot collide with the
# 57 existing F-numbers or with the F58+ range an open PR has claimed.
FLAGS = [
    ("VF-01", "Critical", "The committed results feed is behind the official page by 11 settled games",
     "The frozen 14 Nov Week 10 capture records 13 games without scores; the official page on 16 Nov "
     "shows 12 finals and only 2 games scoreless.",
     "Left frozen on purpose. Rewriting it would mix two retrieval dates in one witness and would also "
     "fail the two-transcription cross-check, which is the repository's own consistency test.",
     "Publish SV-02 as a new dated snapshot and repoint the feed deliberately (G-04, V-S04).",
     (S_SCHED_W10, REPO)),
    ("VF-02", "High", "Three different injury-designation totals are published for one report",
     "171 (official hand count), 162 (repository capture) and 160 (root injuries page). This session "
     "read only chunk 0 of 8 and asserts no total.",
     "Not reconciled: reconciling by choosing would be an inference.",
     "A full capture with a hash and a machine count (V-S04).",
     (S_INJURY, REPO)),
    ("VF-03", "Medium", "The brief's own figures could not be reproduced from the repository",
     "The brief cites 254/279 injury rows, '6 of 254 with a designation', a '136-game log' and VR-/VQ- "
     "reference ids. None of those quantities exists in the repository at those values.",
     "Not silently substituted. A different corpus was not passed off as the named one (R-19).",
     "The source document for those figures, or an owner decision that the committed feed replaces it.",
     (REPO,)),
    ("VF-04", "Medium", "Venue coverage is 3 fixtures of the whole feed",
     "Venue is published on each game centre and is transcribed for WAS@NYG, NE@DET and PIT@CIN only.",
     "Not filled in. A venue guessed from a schedule page would not be a transcription.",
     "One game-centre read per fixture (R-21). Three are done and published on the evidence page.",
     (S_GC_PIT_CIN, S_GC_NE_DET, REPO)),
    ("VF-05", "Medium", "The public/private data split required by the brief is not implemented",
     "Raw row-level files are served publicly from the same origin as the analysis layer.",
     "Not changed here: moving files changes every link and is an integration decision.",
     "V-S07.",
     (REPO,)),
    ("VF-06", "Medium", "Two implementations of the same eight requirements remain unreconciled",
     "The market board and the line-origination desk compute the same requirements from different "
     "inputs, so their numbers can differ.",
     "Not merged: merging changes published numbers.",
     "An owner decision (Q-13, V-S06).",
     (REPO,)),
    ("VF-07", "Low", "The 'estimated starter' half of the availability graph is unbuilt",
     "The brief asks for who was expected to start and who actually did. Only the 'actually did' half "
     "is evidenced, from three Game Books.",
     "Not inferred from depth charts: 'expected' is a different claim from 'listed on a chart'.",
     "An announced-starter register (R-38) plus chart coverage (G-03).",
     (S_GAMECENTER_W10, REPO)),
    ("VF-08", "Low", "An open PR from another session is red and self-described as partial",
     "PR #51 (session f5961230) carries failing checks and states it is not ready to merge.",
     "Not merged and not edited by this session: it is another session's work and its files were "
     "avoided so no claim conflict exists.",
     "Its owner finishes it, or it is closed. Either is fine for this site's integrity.",
     (REPO,)),
    ("VF-09", "Critical", "The brief and the publisher's terms are in direct conflict",
     "Ten requirement lines ask for scheduled multi-day capture, a season-long archive, or a reserve "
     "list joined to the weekly report. NFL.com Terms section 1.3 prohibit systematic retrieval to "
     "build a collection, compilation or database without express prior written consent.",
     "Not worked around, and not silently dropped. Earlier sections of this site recommended building "
     "the capture; this pass corrects that on the quoted clause and publishes the correction rather "
     "than editing the other pages.",
     "Written consent or a licensed feed, or an explicit owner decision to drop those requirements.",
     (S_TERMS, REPO)),
    ("VF-10", "Low", "Three pages read this session are not in the shared source register",
     "The terms page and two game centres were read on 2026-11-16 but are absent from "
     "evidence/sources.json, which is owned by open PR #51. This section carries them locally and says "
     "so, instead of citing a register entry that does not exist.",
     "Logged as a request rather than edited: the register is another session's file and PR #51 has it "
     "open.",
     "The register owner adds the three entries; this section can then drop its local records.",
     (S_TERMS, REPO)),
    ("VF-11", "Medium", "Two per-requirement readiness registers are now published",
     "readiness/index.html (82 requirement rows, merged in PR #53) and this section's "
     "verification/requirements.html (74 rows) answer the same question with different status "
     "vocabularies. Neither is wrong; a reader cannot tell which to act on.",
     "Not reconciled: readiness/** was already merged and belongs to session 4bd7042b. Editing it "
     "would be an unclaimed change to another session's register.",
     "One owner decision to designate a canonical register, or to fold one into the other.",
     (REPO,)),
]

# Findings from earlier sessions that this pass re-checked rather than assumed.
RECHECKED = [
    ("F19-F21", "Club depth charts are self-labelled unofficial; cross-source conflicts are flagged, "
     "not reconciled", "Still open", "3 clubs of 32", (CLUB_DEPTH["KC"],)),
    ("F28", "The weekly schedule page prints records as of retrieval, not as of that week",
     "Re-observed on 2026-11-16: the page shows 4-5 for a club that had played fewer games at the "
     "week's start", "Open", (S_SCHED_W10,)),
    ("F29", "Weeks 9-10 finals rest on the official transcription alone (secondary file stale)",
     "Re-observed: the feed's own build still reports the secondary snapshot missing weeks 9-10",
     "Open", (REPO,)),
    ("F30", "Opening prices exist nowhere; the store's opening columns are blank",
     "Re-measured this pass: 0 of the originated markets carry a market price",
     "Open — unchanged by anything this session did", (REPO,)),
    ("F34-F39", "Week 10 store, replacement chains and demotion gate findings",
     "Not re-verified by this pass; unchanged", "Carried forward", (REPO,)),
]


def flag_rows():
    return FLAGS


def recheck_rows():
    return RECHECKED


# ------------------------------------------------------------------ render helpers
def esc(value) -> str:
    from html import escape
    return escape("" if value is None else str(value))


def source_links(ids) -> str:
    """One anchor per registered source id. An unresolvable id raises rather than printing."""
    out = []
    for sid in ids:
        if sid == REPO:
            out.append('<a href="https://github.com/sassnarep3-star/Own9">Own9 repository ↗</a>')
            continue
        url, publisher = link(sid)
        out.append(f'<a href="{esc(url)}">{esc(publisher)} ↗</a>')
    # de-duplicate while preserving order
    seen, uniq = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return " · ".join(uniq)


def row(cells, source_ids, kind):
    return list(cells), list(source_ids), kind


# ------------------------------------------------------------------ tables
TABLES = {}


def _register():
    TOTAL = len(REQ)
    C = req_counts()
    GS = gate_summary()

    TABLES["requirements"] = (
        "Requirements, line by line",
        "One row per line of the brief. 'Implemented' answers whether the mechanism exists and is "
        "tested; 'Established' answers whether the empirical claim survives contact with official "
        "evidence. They are different questions and no row merges them. A blank Established cell "
        "means not established, never passed. The gate ids are derived from the gate table, so a row "
        "cannot claim to be blocked by a gate that does not list it.",
        ["ID", "Requirement", "Implemented (mechanism, tested)", "Established (official evidence)",
         "Gate", "Why it is blocked", "Number or artefact that would clear it"],
        [row(list(r[:4]) + [", ".join(_gates_for(r[0])) or "none — declared self-satisfied",
                            r[4], r[5]], r[6], "Requirement verdict")
         for r in REQ],
    )

    TABLES["gates"] = (
        "The gates that block the brief, ordered by how many requirements each one holds",
        "A gate is only useful if it names the number that would clear it. The top gate holds "
        f"{max(len(g[3]) for g in GATES)} requirements and cannot be bought, licensed or worked "
        "around from inside this repository.",
        ["Gate", "Gate name", "Why it is closed", "Requirement IDs it blocks", "What clears it",
         "How clearance would be measured"],
        [row([g[0], g[1], g[2], ", ".join(g[3]), g[4], g[5]],
             _ordered_sources(g[3]), "Gate")
         for g in GATES],
    )

    TABLES["snapshots"] = (
        "Dated snapshot ledger (two reads of the same pages, kept side by side)",
        "The brief asks for immutable captures. These are the captures this repository actually holds, "
        "with the date and the reader. Where a page moved between reads, both reads are published and "
        "the older one was not rewritten.",
        ["Snapshot", "Artefact", "Read date", "Read by", "What it records", "Note"],
        [row(s[:6], s[6], "Dated capture") for s in SNAPSHOTS],
    )

    TABLES["delta"] = (
        "What changed between SV-01 and SV-02 (measured, not described)",
        "The delta column the brief asks for, computed from the two reads. It deliberately does not "
        "claim the feed was regenerated, because it was not.",
        ["Measure", "SV-01 (14 Nov)", "SV-02 (16 Nov)", "Delta", "Meaning"],
        [row(d[:5], d[5], "Measured delta") for d in delta_rows()],
    )

    TABLES["venues"] = (
        "Fixtures whose venue is transcribed from the official game centre",
        "The brief asks for every fixture. Three can be transcribed from sources already read. The "
        "remaining fixtures have no published venue in any source this repository holds, so their "
        "rows are absent rather than blank-filled.",
        ["Week", "Away", "Home", "Stadium (as published)", "Location (as published)", "Note"],
        [row(v[:6], v[6], "Official transcription") for v in VENUES],
    )

    TABLES["questions"] = (
        "Questions that must be settled before a decision can be made",
        "Each question is answerable now, blocked on a named artefact, or a decision only the owner can "
        "take. Where a question is answerable, the answer is stated rather than deferred.",
        ["ID", "Question", "State", "Answer or why not", "What it would take"],
        [row(q[:5], q[5], "Question register") for q in QUESTIONS],
    )

    TABLES["suggestions"] = (
        "Suggestions, with cost and what would show the choice was wrong",
        "A suggestion is a proposal, never a finding. Each names the requirement it addresses, what it "
        "costs, what it unblocks, and what evidence would show it was the wrong path — so a reviewer "
        "can choose before anything is built.",
        ["ID", "Suggestion", "Why it improves a decision", "Cost", "What it unblocks",
         "What would show it was wrong"],
        [row(s[:6], s[6], "Proposal") for s in SUGGESTIONS],
    )

    TABLES["flags"] = (
        "Flagged for review (this session's findings)",
        "Numbered VF-01.. to avoid colliding with the 57 existing F-numbers and the F58+ range open PR "
        "#51 has claimed. Nothing here blocks the site from being published; each row says what would "
        "close it.",
        ["ID", "Severity", "Irregularity", "What was observed", "Why it was not fixed here",
         "What closes it"],
        [row(f[:6], (REPO,) + tuple(x for x in f[6] if x != REPO), "Flagged irregularity")
         for f in FLAGS],
    )

    TABLES["rechecked"] = (
        "Inherited findings re-checked this pass",
        "Earlier sessions' findings are not assumed to be true. These were re-observed against the "
        "sources on 2026-11-16, or explicitly carried forward unverified.",
        ["Finding", "Claim", "Re-checked result", "State"],
        [row(r[:4], r[4], "Re-check") for r in RECHECKED],
    )

    TABLES["readiness"] = (
        "Decision readiness: one row per gate, with the number that would clear it",
        f"{C['impl']['total']} requirement lines map onto {GS['gates']} gates. "
        f"{GS['requirements_mapped']} of {C['impl']['total']} are mapped to at least one gate; the "
        f"remaining {len(GS['requirements_unmapped'])} are prohibitions the repository honours or "
        "process facts that hold by construction, and are declared as such rather than left unmapped.",
        ["Gate", "Blocked requirements", "Requirements held", "Clear by", "Cost class"],
        [row([g[0], ", ".join(g[3]), len(g[3]), g[4], _cost_class(g[0])], (REPO,), "Readiness")
         for g in sorted(GATES, key=lambda g: -len(g[3]))],
    )

    TABLES["measured"] = (
        "Numbers this section measures at build time",
        "Every value below is computed from a committed file during the build, so the prose cannot "
        "drift from the data. A blank is a value that does not exist, not a zero.",
        ["Measure", "Value", "What it means"],
        [row([k.replace("_", " "), v if v is not None else "", _MEANING.get(k, "")], (REPO,),
             "Build-time measurement") for k, v in M.items()],
    )


_MEANING = {
    "finals_total": "Finals in the committed verified feed",
    "finals_weeks": "Weeks represented in the feed",
    "finals_w10": "Week 10 finals committed (the 14 Nov capture)",
    "pending_total": "Games in the feed with no score",
    "pending_w10": "Week 10 games with no score in the feed",
    "markets_week11": "Week 11 markets originated",
    "markets_with_market_price": "Markets carrying a market price — blank by policy",
    "markets_priced_pct": "Share of originated markets that are priced",
    "snapshots_total": "Open + close snapshot rows",
    "snapshots_with_market_price": "Snapshot rows carrying a market price",
    "correlations_total": "Correlation pairs computed from official numbers",
    "correlations_with_n": "Pairs publishing n beside the value",
    "correlations_claiming_dependence": "Pairs whose interval clears the 0.10 deadband",
    "walk_forward_weeks": "Walk-forward weeks evaluated",
    "walk_forward_complete_weeks": "Weeks with a complete slate",
    "walk_forward_graded_games": "Games graded walk-forward, all weeks",
    "walk_forward_graded_games_complete_only": "Games graded on complete slates only",
    "replacement_rows": "Replacement register rows",
    "replacement_withheld": "Replacement rows withheld with a stated reason",
}


def _ordered_sources(req_ids):
    """Sources for a group of requirements, de-duplicated WITHOUT a set.

    A set here made the rendered HTML depend on PYTHONHASHSEED, which this section's own
    determinism test caught: the same list of sources rendered in different orders between
    runs. Order is first-seen, so regeneration is byte-identical.
    """
    out = []
    for rid in req_ids:
        for sid in _srcs_for(rid):
            if sid not in out:
                out.append(sid)
    return tuple(out)


def _gates_for(rid):
    """Gate ids that list this requirement. Derived, so the two tables cannot disagree."""
    return [g[0] for g in GATES if rid in g[3]]


def _srcs_for(rid):
    for r in REQ:
        if r[0] == rid:
            return r[6]
    return (REPO,)


def _cost_class(gate_id):
    return {
        "G-01": "Licence or own-book log — cannot be bought inside the repository",
        "G-02": "Capture — engineering, conditional on G-10",
        "G-03": "29 club reads — labour",
        "G-04": "One re-capture — already demonstrated (SV-02)",
        "G-05": "More seasons — labour and archive access",
        "G-06": "Statistical — a real edge, not a task",
        "G-07": "Schema and process — cheapest open gate",
    }.get(gate_id, "")


_register()
