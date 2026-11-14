"""Deterministic static renderer; no network calls, no invented NFL metrics."""
import json
import sys
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.registers import impact_rank  # noqa: E402
SOURCES = {s['id']: s for s in json.loads((ROOT/'evidence/sources.json').read_text())}
SUGGESTIONS = json.loads((ROOT/'research/suggestions.json').read_text())
QUESTIONS = json.loads((ROOT/'research/decision-register.json').read_text())
BRIEF = json.loads((ROOT/'research/decision-brief.json').read_text())
AVAILABILITY = json.loads((ROOT/'evidence/lineups/was-nyg-2026-week-9-10.json').read_text())
# Map the evidence file's own citation keys onto the shared source register.
GAMEBOOK = {
    'gamebook_week9_lar_was': 'nfl-gamebook-w9-lar-was',
    'gamebook_week9_nyg_phi': 'nfl-gamebook-w9-nyg-phi',
    'gamebook_week10_was_nyg': 'nfl-gamebook-w10',
    'injury_week10': 'nfl-injury',
}
INJURY = json.loads((ROOT/'evidence/availability/injury-report-2026-week-10.json').read_text())
PAGES = {}
# Pages whose tables rest on documents retrieved on 14 Nov 2026.
KEEP_DATE_14 = {'decision.html','questions.html','availability.html','suggestions.html',
                'decisions-questions.html','sources.html','flags.html','audit.html','injuries.html',
               'lines.html','availability-evidence.html','question-ledger.html','suggestion-costs.html'}

# Navigation grouped by what the reader is trying to do, not by file order.
NAV_GROUPS = [
    ('Decide', [('decision.html','Decision brief'),('questions.html','Question register'),('decisions-questions.html','Decision review'),('question-ledger.html','Question ledger')]),
    ('Evidence', [('index.html','Overview'),('availability.html','Availability tracker'),('injuries.html','Injuries & depth'),('availability-evidence.html','Availability sources'),('lines.html','Own lines'),('data.html','Data requirements'),('sources.html','Sources')]),
    ('Research', [('strategies.html','Strategies'),('correlations.html','Correlations'),('validation.html','Validation'),('leaderboard.html','Leaderboard')]),
    ('Review', [('suggestions.html','Suggestions'),('suggestion-costs.html','Suggestion costs'),('flags.html','Flagged for review'),('audit.html','Repository audit')]),
]


# --- Injury & depth tracking data: transcribed verbatim from the official NFL Week 10 2026
# --- injury report (https://www.nfl.com/injuries/, retrieved 2026-11-14, 8 chunks). Only players
# --- with an explicit Game Status (Out / Doubtful / Questionable) are included; a blank injury
# --- description means the report listed no injury, not that the player is healthy.
WEEK10 = ('Week 10 · 2026 season · retrieved 2026-11-14 UTC')
INJ = [
 # (team, player, position, injuries, practice status, game status) — order follows the report page
 ('WAS','Lucas Patrick','C','Concussion','Did Not Participate In Practice','Out'),
 ('WAS','Colson Yankoff','TE','Knee','Did Not Participate In Practice','Out'),
 ('NYG','Malik Harrison','LB','Groin','Limited Participation in Practice','Questionable'),
 ('NE','Ben Brown','C','Knee','Did Not Participate In Practice','Out'),
 ('NE','A.J. Brown','WR','Ankle, Knee','Limited Participation in Practice','Questionable'),
 ('NE','Kevin Byard','S','Chest','Full Participation in Practice','Questionable'),
 ('NE','Carlton Davis III','CB','Knee','Did Not Participate In Practice','Out'),
 ('NE','Reggie Gilliam','FB','Knee','Limited Participation in Practice','Questionable'),
 ('NE','TreVeyon Henderson','RB','Illness','Did Not Participate In Practice','Out'),
 ('NE','Cameron Latu','TE','Back','Limited Participation in Practice','Questionable'),
 ('NE','Walter Rouse','T','Concussion','Limited Participation in Practice','Questionable'),
 ('NE','Brenden Schooler','S','Hamstring','Limited Participation in Practice','Questionable'),
 ('NE','Rhamondre Stevenson','RB','Knee','Limited Participation in Practice','Questionable'),
 ('NE','Greg Van Roten','G','Hamstring','Full Participation in Practice','Questionable'),
 ('NE','Charles Woods','CB','Hamstring','Full Participation in Practice','Questionable'),
 ('DET','Kerby Joseph','S','Knee','Did Not Participate In Practice','Out'),
 ('DET','Cade Mays','C','Ankle','Did Not Participate In Practice','Out'),
 ('DET','D.J. Reed','CB','Hip','Did Not Participate In Practice','Out'),
 ('DET','Amon-Ra St. Brown','WR','Rib','Limited Participation in Practice','Questionable'),
 ('DET','Sione Vaki','RB','Ankle','Limited Participation in Practice','Questionable'),
 ('KC','Mansoor Delane','CB','Shoulder','Full Participation in Practice','Questionable'),
 ('KC','Jaylon Moore','T','Ankle','Did Not Participate In Practice','Out'),
 ('KC','Omarr Norman-Lott','DT','Knee','Limited Participation in Practice','Out'),
 ('KC','Jaydn Ott','RB','Hamstring','Limited Participation in Practice','Questionable'),
 ('KC','Kenneth Walker III','RB','Groin','Did Not Participate In Practice','Questionable'),
 ('KC','Peter Woods','DT','Neck','Did Not Participate In Practice','Out'),
 ('ATL','Zachariah Branch','WR','Hamstring','Did Not Participate In Practice','Out'),
 ('ATL','Divine Deablo','LB','Forearm','Did Not Participate In Practice','Doubtful'),
 ('ATL','Gervon Dexter Sr.','DT','Illness','Limited Participation in Practice','Questionable'),
 ('ATL','James Pearce Jr.','DE','Back','Limited Participation in Practice','Questionable'),
 ('ATL','Josh Woods','LB','Ankle','Full Participation in Practice','Questionable'),
 ('MIN','Jordan Addison','WR','Thumb','Limited Participation in Practice','Questionable'),
 ('MIN','Blake Cashman','LB','Concussion','Limited Participation in Practice','Out'),
 ('MIN','T.J. Hockenson','TE','Wrist, Chest','Did Not Participate In Practice','Out'),
 ('MIN','Tyrion Ingram-Dawkins','DT','Ankle','Did Not Participate In Practice','Out'),
 ('MIN','Jauan Jennings','WR','Calf','Did Not Participate In Practice','Out'),
 ('MIN','Josh Metellus','S','Shoulder','Limited Participation in Practice','Questionable'),
 ('MIN','Kyler Murray','QB','Hamstring','Did Not Participate In Practice','Out'),
 ('MIN','Kyle Van Noy','LB','Calf','Limited Participation in Practice','Questionable'),
 ('GB','Chris Brooks','RB','Ankle','Limited Participation in Practice','Questionable'),
 ('GB','Javon Bullard','S','Ankle, Knee','Limited Participation in Practice','Questionable'),
 ('GB','Zaire Franklin','LB','Shin','Did Not Participate In Practice','Doubtful'),
 ('GB','Travis Glover','G','Knee','Limited Participation in Practice','Questionable'),
 ('GB','Josh Jacobs','RB','Finger','Did Not Participate In Practice','Out'),
 ('GB','Xavier McKinney','S','Foot','Limited Participation in Practice','Questionable'),
 ('GB','Skyy Moore','WR','Ankle','Limited Participation in Practice','Questionable'),
 ('GB','Micah Parsons','LB','Knee, Illness','Limited Participation in Practice','Out'),
 ('GB','Sean Rhyan','C','Ankle','Did Not Participate In Practice','Out'),
 ('GB','Lukas Van Ness','LB','Back','Limited Participation in Practice','Questionable'),
 ('GB','Josh Whyle','TE','Concussion','Did Not Participate In Practice','Out'),
 ('GB','Kevin Zeitler','G','Ankle, Triceps','Did Not Participate In Practice','Questionable'),
 ('JAX','Jessie Bates','S','Not injury related - resting player','Limited Participation in Practice','Out'),
 ('JAX','Jordan Davis','DT','Not injury related - resting player','Limited Participation in Practice','Out'),
 ('JAX','BJ Green II','DE','Forearm','Full Participation in Practice','Out'),
 ('JAX','Robert Hainsey','C','Concussion','Limited Participation in Practice','Questionable'),
 ('TEN','Cody Barton','LB','Concussion','Did Not Participate In Practice','Out'),
 ('TEN','Anthony Hill Jr.','LB','Neck','Did Not Participate In Practice','Out'),
 ('TEN','Peter Skoronski','G','Hamstring','Did Not Participate In Practice','Out'),
 ('TEN','Tyjae Spears','RB','Knee','Full Participation in Practice','Questionable'),
 ('TEN','Carnell Tate','WR','Shoulder','Did Not Participate In Practice','Out'),
 ('TEN','Tommy Townsend','P','Knee, Achilles','Did Not Participate In Practice','Out'),
 ('BUF','Christian Benford','CB','Wrist','Full Participation in Practice','Questionable'),
 ('BUF','Spencer Brown','T','Ankle','Did Not Participate In Practice','Doubtful'),
 ('BUF','Sam Franklin Jr.','S','Shoulder','Limited Participation in Practice','Questionable'),
 ('BUF','Jordan Hancock','CB','Hamstring','Full Participation in Practice','Questionable'),
 ('BUF','Tyrell Shavers','WR','Knee','Full Participation in Practice','Questionable'),
 ('NYJ','Jarvis Brownlee Jr.','CB','Illness','Limited Participation in Practice','Questionable'),
 ('NYJ','Omar Cooper Jr.','WR','Ankle','Full Participation in Practice','Questionable'),
 ('NYJ','Adonai Mitchell','WR','Knee','Full Participation in Practice','Questionable'),
 ('NYJ','Joseph Ossai','DE','Ankle','Full Participation in Practice','Questionable'),
 ('NYJ','VJ Payne','S','Knee','Full Participation in Practice','Questionable'),
 ('NYJ','Harrison Phillips','DT','Ankle','Full Participation in Practice','Questionable'),
 ('NYJ','Trevin Wallace','LB','Groin','Did Not Participate In Practice','Out'),
 ('NYJ','Garrett Wilson','WR','Concussion','Full Participation in Practice','Questionable'),
 ('NYJ','Nahshon Wright','CB','Back','Full Participation in Practice','Questionable'),
 ('MIA','Darrell Baker Jr.','CB','Knee','Full Participation in Practice','Questionable'),
 ('MIA','Chris Bell','WR','Knee','Did Not Participate In Practice','Doubtful'),
 ('MIA','Aaron Brewer','C','Concussion','Did Not Participate In Practice','Out'),
 ('MIA','Jared Wayne','WR','Quadricep','Did Not Participate In Practice','Out'),
 ('IND','Mo Alie-Cox','TE','Groin','Did Not Participate In Practice','Out'),
 ('IND','Jaylon Carlies','LB','Neck','Did Not Participate In Practice','Out'),
 ('IND','Akeem Davis-Gaither','LB','Knee','Did Not Participate In Practice','Out'),
 ('IND','Arden Key','DE','Hamstring','Full Participation in Practice','Questionable'),
 ('IND','Will Mallory','TE','Hamstring','Limited Participation in Practice','Questionable'),
 ('IND','Luke Rhodes','LS','Hamstring','Did Not Participate In Practice','Out'),
 ('IND','Jerry Tillery','DT','Calf','Did Not Participate In Practice','Out'),
 ('IND','Jalen Travis','T','Knee','Did Not Participate In Practice','Out'),
 ('CAR','Jonathon Brooks','RB','Groin','Limited Participation in Practice','Doubtful'),
 ('CAR','Brady Christensen','G','Hamstring','Full Participation in Practice','Questionable'),
 ('CAR','Mike Jackson','CB','Groin','Limited Participation in Practice','Doubtful'),
 ('CAR','Will Lee III','CB','Hamstring','Limited Participation in Practice','Questionable'),
 ('CAR','Xavier Legette','WR','Knee','Full Participation in Practice','Questionable'),
 ('CAR','Bobby Okereke','LB','Foot','Did Not Participate In Practice','Out'),
 ('CAR','Jaelan Phillips','LB','Hamstring','Full Participation in Practice','Questionable'),
 ('NO','CJ Donaldson','RB','Shoulder','Did Not Participate In Practice','Out'),
 ('NO','Martin Emerson','CB','Shin','Limited Participation in Practice','Questionable'),
 ('NO','Travis Etienne','RB','Hamstring','Full Participation in Practice','Questionable'),
 ('NO','Taliese Fuaga','T','Knee','Did Not Participate In Practice','Out'),
 ('NO','Erik McCoy','C','Biceps','Did Not Participate In Practice','Out'),
 ('NO','Christen Miller','DT','Knee','Did Not Participate In Practice','Out'),
 ('HOU','Azeez Al-Shaair','LB','Groin, Not injury related - personal matter','Did Not Participate In Practice','Out'),
 ('HOU','Will Anderson Jr.','DE','Ankle','Did Not Participate In Practice','Questionable'),
 ('HOU','Trent Brown','T','Wrist, Illness','Did Not Participate In Practice','Questionable'),
 ('HOU','Marvin Harrison Jr.','WR','Hamstring','Did Not Participate In Practice','Out'),
 ('HOU','Jake Hummel','LB','Groin','Full Participation in Practice','Questionable'),
 ('HOU','Danielle Hunter','DE','Hamstring','Did Not Participate In Practice','Out'),
 ('HOU','Brevin Jordan','TE','Finger, Foot','Did Not Participate In Practice','Out'),
 ('HOU','David Montgomery','RB','Groin','Full Participation in Practice','Questionable'),
 ('HOU','Keylan Rutledge','G','Neck, Shoulder','Did Not Participate In Practice','Out'),
 ('HOU','Jaylin Smith','CB','Hamstring','Full Participation in Practice','Questionable'),
 ('HOU','Wyatt Teller','G','Illness, Back','Limited Participation in Practice','Questionable'),
 ('CLE','Denzel Boston','WR','Toe','Limited Participation in Practice','Questionable'),
 ('CLE','Michael Burton','FB','Calf','Did Not Participate In Practice','Out'),
 ('CLE','Ronnie Hickman Jr.','S','Concussion','Did Not Participate In Practice','Out'),
 ('LAR','Davis Allen','TE','Oblique','Limited Participation in Practice','Questionable'),
 ('LAR','Steve Avila','G','Hamstring','Did Not Participate In Practice','Out'),
 ('LAR','Joe Cardona','LS','Ankle','Limited Participation in Practice','Questionable'),
 ('LAR','Kamren Curl','S','Toe','Limited Participation in Practice','Questionable'),
 ('LAR','Terrance Ferguson','TE','Ankle, Hamstring','Did Not Participate In Practice','Out'),
 ('LAR','Myles Garrett','LB','Knee, Not injury related - resting player','Did Not Participate In Practice','Questionable'),
 ('LAR','Trent McDuffie','CB','Back','Limited Participation in Practice','Questionable'),
 ('AZ','Zachary Carter','DT','Knee','Limited Participation in Practice','Out'),
 ('AZ','Hjalte Froholdt','C','Concussion','Did Not Participate In Practice','Out'),
 ('AZ','Jon Gaines II','G','Ankle','Did Not Participate In Practice','Out'),
 ('AZ','Hunter Long','TE','Knee','Limited Participation in Practice','Questionable'),
 ('AZ','Roy Lopez','DT','Toe, Ankle','Limited Participation in Practice','Questionable'),
 ('AZ','Max Melton','CB','Knee, Hand','Limited Participation in Practice','Questionable'),
 ('AZ','Darius Robinson','DT','Wrist','Limited Participation in Practice','Questionable'),
 ('AZ','Jayden Williams','T','Knee','Limited Participation in Practice','Questionable'),
 ('AZ','Andrew Wingard','S','Groin','Did Not Participate In Practice','Questionable'),
 ('SEA','Charles Cross','T','Ankle','Did Not Participate In Practice','Out'),
 ('SEA','Sam Darnold','QB','Ribs, Quadricep','Did Not Participate In Practice','Out'),
 ('SEA','Quenton Nelson','G','Knee','Did Not Participate In Practice','Out'),
 ('SEA','Leonard Williams','DT','Stinger','Did Not Participate In Practice','Out'),
 ('LV','Thomas Booker','DT','Ankle','Full Participation in Practice','Questionable'),
 ('LV','Dont\'e Thornton Jr.','WR','Back','Did Not Participate In Practice','Questionable'),
 ('SF','Mike Evans','WR','Achilles','Did Not Participate In Practice','Out'),
 ('SF','Renardo Green','CB','Back','Limited Participation in Practice','Questionable'),
 ('SF','Dre Greenlaw','LB','Knee','Limited Participation in Practice','Questionable'),
 ('SF','Nate Hobbs','CB','Groin','Full Participation in Practice','Questionable'),
 ('SF','Deommodore Lenoir','CB','Foot','Limited Participation in Practice','Questionable'),
 ('SF','Upton Stout','CB','Shoulder, Neck','Limited Participation in Practice','Questionable'),
 ('SF','C.J. West','DT','Knee','Full Participation in Practice','Questionable'),
 ('SF','Trent Williams','T','Shoulder','Did Not Participate In Practice','Questionable'),
 ('DAL','DaRon Bland','CB','Ankle','Limited Participation in Practice','Questionable'),
 ('DAL','Jonathan Bullard','DT','Calf','Full Participation in Practice','Questionable'),
 ('DAL','Alijah Clark','S','Illness','Did Not Participate In Practice','Questionable'),
 ('DAL','Donovan Ezeiruaku','LB','Ankle','Did Not Participate In Practice','Out'),
 ('DAL','Jake Ferguson','TE','Knee, Ankle','Did Not Participate In Practice','Out'),
 ('DAL','Tyler Goodson','RB','Ankle, Knee','Did Not Participate In Practice','Out'),
 ('DAL','P.J. Locke','S','Concussion','Did Not Participate In Practice','Out'),
 ('DAL','Jonathan Mingo','WR','Ankle','Did Not Participate In Practice','Out'),
 ('DAL','Devin Moore','CB','Hip','Full Participation in Practice','Questionable'),
 ('DAL','Joey Porter Jr.','CB','Ankle, Foot','Limited Participation in Practice','Questionable'),
 ('DAL','Juanyeh Thomas','S','Hamstring','Did Not Participate In Practice','Doubtful'),
 ('PIT','Derrick Harmon','DT','Foot','Full Participation in Practice','Questionable'),
 ('CIN','Jalen Davis','CB','Hamstring','Full Participation in Practice','Doubtful'),
 ('CIN','Kyle Dugger','S','Quadricep','Did Not Participate In Practice','Out'),
 ('CIN','Andrei Iosivas','WR','Thumb','Full Participation in Practice','Doubtful'),
 ('CIN','Brian Parker II','G','Knee','Full Participation in Practice','Doubtful'),
]
SLATE = [  # games as listed on the same report page (team order, records, kickoff and network verbatim)
 ('WAS','3-5-1','NYG','5-3-1','Thursday, November 12th · 8:15 PM EST','Prime Video'),
 ('NE','5-4','DET','6-2','Sunday, November 15th · 9:30 AM EST','FOX, FOX Deportes'),
 ('KC','6-2','ATL','3-6','Sunday, November 15th · 1:00 PM EST','CBS'),
 ('MIN','6-2','GB','6-3','Sunday, November 15th · 1:00 PM EST','FOX'),
 ('JAX','6-2','TEN','1-7','Sunday, November 15th · 1:00 PM EST','FOX'),
 ('BUF','7-1','NYJ','2-7','Sunday, November 15th · 1:00 PM EST','CBS'),
 ('MIA','1-7','IND','2-7','Sunday, November 15th · 1:00 PM EST','CBS'),
 ('CAR','3-5','NO','3-5','Sunday, November 15th · 1:00 PM EST','FOX'),
 ('HOU','3-5','CLE','5-4','Sunday, November 15th · 1:00 PM EST','FOX'),
 ('LAR','5-4','AZ','3-6','Sunday, November 15th · 4:05 PM EST','CBS'),
 ('SEA','5-4','LV','4-5','Sunday, November 15th · 4:05 PM EST','CBS'),
 ('SF','7-1','DAL','4-5','Sunday, November 15th · 4:25 PM EST','FOX, FOX Deportes'),
 ('PIT','6-2','CIN','6-2','Sunday, November 15th · 8:20 PM EST','NBC, Universo'),
 ('LAC','0-8','BAL','4-5','Monday, November 16th · 8:15 PM EST','ESPN, ABC, ESPN2, ESPN Deportes'),
]
UNIT = {'QB':'Offense','RB':'Offense','FB':'Offense','WR':'Offense','TE':'Offense','T':'Offensive line','G':'Offensive line','C':'Offensive line',
        'DE':'Defense','DT':'Defense','NT':'Defense','LB':'Defense','CB':'Defense','S':'Defense','DB':'Defense',
        'LS':'Special teams','P':'Special teams','K':'Special teams','H':'Special teams','KR':'Special teams','PR':'Special teams'}
SLATE_TEAMS = [(a,ar,b,br) for a,ar,b,br,_n,_tv in SLATE]

def burden_rows():
    out=[]
    order=[t for a,_,b,_ in SLATE_TEAMS for t in (a,b)]
    for team in order:
        rows=[r for r in INJ if r[0]==team]
        def cnt(pred): return sum(1 for r in rows if pred(r))
        out.append((team,
            cnt(lambda r:r[5]=='Out'), cnt(lambda r:r[5]=='Doubtful'), cnt(lambda r:r[5]=='Questionable'),
            cnt(lambda r:UNIT.get(r[2])=='Defense'), cnt(lambda r:UNIT.get(r[2]) in ('Offense','Offensive line')), cnt(lambda r:UNIT.get(r[2])=='Special teams'),
            len(rows)))
    tot=[sum(x[i] for x in out) for i in range(1,8)]
    out.append(('League total',*tot))
    return out



def table(title, headers, rows):
    output = f'<h2>{e(title)}</h2><div class="table-wrap"><table><caption class="sr-only">{e(title)}</caption><thead><tr>'
    output += ''.join(f'<th scope="col">{e(h)}</th>' for h in [*headers, 'Evidence / scope'])
    output += '</tr></thead><tbody>'
    for i, (cells, refs, kind) in enumerate(rows,1):
        output += f'<tr id="{e(title.lower().replace(" ","-"))}-{i}">'
        for j,c in enumerate(cells):
            tag = 'th scope="row"' if j == 0 else 'td'
            close = 'th' if j == 0 else 'td'
            output += f'<{tag}>{e(str(c)) if c is not None else ""}</{close}>'
        links = ' · '.join(f'<a href="{e(SOURCES[r]["url"],quote=True)}">{e(SOURCES[r]["publisher"])} ↗</a>' for r in refs)
        output += f'<td><span class="evidence-kind">{e(kind)}</span>{links}</td></tr>\n'
    return output + '</tbody></table></div>'


def row(cells, refs=('repo',), kind='Project record'):
    return cells, refs, kind


def page(file, label, title, intro, content):
    PAGES[file] = (label,title,intro,content)


page('index.html','Overview','Evidence first.\nAn edge must be earned.',
     'An NFL line-origination lab for game singles, player props and joint bets. Built to test skill—not reward a lucky streak.',
     '''<div class="notice"><strong>Research framework · no validated strategies</strong><p>No verified historical executable odds or point-in-time paired dataset was obtained. NFL lines, measured correlations, test scores and cash rewards are intentionally blank. No wagering is enabled.</p></div>
<div class="cards"><a href="strategies.html"><span>01 / HYPOTHESES</span><b>Signal registry</b><p>Singles, props & joint models</p></a><a href="validation.html"><span>02 / DISCIPLINE</span><b>Seven evidence gates</b><p>Fail closed. Publish all trials.</p></a><a href="correlations.html"><span>03 / DEPENDENCE</span><b>Correlation lab</b><p>Paired evidence, not assumptions</p></a><a href="leaderboard.html"><span>04 / COMPETITION</span><b>Evidence leaderboard</b><p>No eligible entries, no awards</p></a></div><div class="cards"><a href="injuries.html"><span>05 / AVAILABILITY</span><b>Injuries & depth</b><p>Week 10 2026 verified snapshot</p></a><a href="questions.html"><span>06 / REVIEW QUEUE</span><b>Decision questions</b><p>Known, unknown, and next steps</p></a><a href="data.html"><span>07 / INPUTS</span><b>Data requirements</b><p>Acquisition contract, fail closed</p></a><a href="audit.html"><span>08 / RECORDS</span><b>Repository audit</b><p>Implementation and integration log</p></a></div>'''
     + table('Executive summary',['Decision area','Finding','Disposition'],[
         row(['Originate NFL lines','A distribution-first design is specified; tested pricing primitives exist. No officially verified fitted NFL probability model or numerical line is available in this dashboard.','Implemented math / model not implemented']),
         row(['Useful signals','Opponent-adjusted efficiency, pace, participation and shared game script are hypotheses; no direction, effect size or profitability is asserted.','Research proposals'],('nfl-stats','nfl-injury'),'Context only / proposed'),
         row(['Skill versus luck','Use sealed future periods, proper scoring, multiplicity control and uncertainty. These can test evidence of skill, not eliminate chance.','No skill certification'],('holdout','brier','multiplicity'),'Method support / policy proposed'),
         row(['Correlation','No verified aligned sample was obtained. Descriptive Pearson/phi code is tested only on synthetic examples.','Unverified NFL values'],('pearson','repo'),'Formula support / project record'),
         row(['Competition rewards','Separate target-matched tracks and hypothetical recognition badges are proposed. No sponsor, cash pool or awards exist.','No funded program']),
         row(['Injury & depth tracking','Official Week 10 2026 injury report transcribed with '+str(len(INJ))+' explicit game-status entries; club depth charts (KC, SEA, DET) verified 2026-11-14; starter→replacement derivation demonstrated. Historical archives and certified depth remain missing.','Snapshot + framework'],('nfl-injury-w10','chiefs-depth','repo'),'Direct publisher / project record'),
         row(['Injury & depth tracking','Official Week 10 2026 injury report transcribed with '+str(len(INJ))+' explicit game-status entries across all 14 listed games; official club depth charts (KC, SEA, DET) retrieved 2026-11-14; starter→next-string derivations published with both sources. Historical archives and certified game-day depth remain missing.','Snapshot + framework'],('nfl-injury-w10','chiefs-depth','repo'),'Direct publisher / project record'),
         row(['Executive recommendation','Continue as a paper-research lab. Missing provenance, prices or validation blocks eligibility—not publication of limitations.','No bets recommended'])
     ]) + '<p class="download">Read the <a href="questions.html">decision questions &amp; improvement suggestions</a>, <a href="docs/RESEARCH_SPEC.md">full research specification</a>, and <a href="audit.html">repository audit</a>. All empirical gaps appear on <a href="flags.html">Flagged for Review</a>.</p>'
     + table('Related sections in this repository',['Section','Contents','Publisher / session record','Integration state'],[
         row(['Additive dashboard','Independent source-linked lab with pricing primitives and 11 gates; publishes at /Own9/site/.','Repository record','Live subsite — linked, not merged'],('repo',),'Project record'),
         row(['Strict-source lab','Additive strict-lab research section with published evidence flags F01-F12.','Repository record','Live subsite — linked, not merged'],('repo',),'Project record'),
         row(['Signal research','Secondary-source pipeline: 15 strategies, walk-forward own-line model; findings flagged uncertified.','Repository record','Live subsite — linked, not adopted'],('repo',),'Project record'),
         row(['Own9 research lab','Separate pipeline and 12-page dashboard; empirical figures flagged unverified.','Repository record','Live subsite — linked, not adopted'],('repo',),'Project record'),
         row(['Release checks','Independent structural/deployment review reports and snapshots.','Repository record','Live subsite — linked'],('repo',),'Project record'),
         row(['Independent audit','Five-page official-source audit of the original 28-row dashboard, integrated from PR #18 (stale-session takeover, 2026-11-14).','Repository record','Live subsite — linked'],('repo',),'Project record')
     ]))

page('strategies.html','Strategies','The signal registry.',
     'Predeclared research candidates. These are designs to test, not discovered edges or recommendations. Contextual references do not endorse a strategy.',
     table('Candidate strategies',['ID / track','Proposed signal and model','Required ablation / falsification','State'],[
         row(['G1 · Game single','Opponent-adjusted past efficiency, pace and availability → regularized joint score distribution → moneyline, spread and total.','Remove efficiency, pace and availability one at a time; compare frozen baseline on later weeks.','Unvalidated'],('nfl-stats','nfl-injury'),'Official input categories / proposal'),
         row(['P1 · Player prop','Participation × opportunities × conditional efficiency; separate count and yardage distributions.','Exposure-only baseline; remove availability adjustments; audit missing participation and player-role changes.','Unvalidated'],('nfl-stats','nfl-injury'),'Official input categories / proposal'),
         row(['X1 · Cross-game parlay','Common-week latent scenarios → joint win probability. Use actual combo quote, not multiplied marginal odds.','Compare joint model with independence baseline; test held-out joint-event calibration.','Unvalidated'],('pearson','repo'),'Dependence background / proposal'),
         row(['S1 · Same-game prop combo','Shared plays, game script, team pass/rush and target allocation → joint player outcomes with accounting constraints.','Remove shared effects; check feasible combinations, joint calibration and every settlement rule.','Unvalidated'],('nfl-stats','pearson'),'Input / dependence context only'),
         row(['A1 · Selective abstention','Withhold when data, quoted price or model support is missing; freeze any edge cutoff before the final test.','Publish abstention count and coverage; evaluate the complete decision rule, not selected winners.','Unvalidated'],('holdout','repo'),'Overfit support / policy proposed')
     ]) + table('Line origination contract',['Market / calculation','Definition','Limit'],[
         row(['Home spread','With M = home score − away score and signed home handicap h, cover = P(M+h>0); push = P(M+h=0).','A fair handicap is not generally the mean margin. Numerical line unavailable.'],('repo',),'Project mathematical specification'),
         row(['Total / prop over','Sum mass strictly above the quoted threshold; retain equality as a separate push state.','Must specify overtime, participation and void rules. No numerical threshold inferred.'],('repo',),'Project mathematical specification'),
         row(['Fair decimal / expected return','Dfair = 1 + Ploss/Pwin. Net EV per unit = Pwin×(D−1) − Ploss − cost, with full refunds earning zero.','Undefined if Pwin=0; reduced-leg payouts require a full state model. Algebra tested, not an edge.'],('repo',),'Project algebra / unit tested'),
         row(['Market baseline','Normalize inverse decimal prices over every mutually exclusive exhaustive no-push outcome.','Proportional de-vig is a declared comparison convention, not verified true probability.'],('repo',),'Project baseline convention')
     ]))

page('validation.html','Validation','Seven gates. No shortcuts.',
     'Proposed acceptance policy. Every gate is mandatory; a missing value is not a pass. Unit tests validate software arithmetic—not NFL skill.',
     table('Validation gates',['Gate','Acceptance requirement','Artifact / current state'],[
         row(['1 · Provenance','All evaluated records have official outcome URLs, IDs, units, source timestamps, raw hashes and rule snapshots; quarantine missing required records.','No qualifying dataset · Not run'],('nfl-stats','repo'),'Data context / proposed policy'),
         row(['2 · Point in time','Features and quotes available before issuance and kickoff; freeze forecasts; no same-game fold leakage.','No forecast/quote ledger · Not run'],('holdout','repo'),'Leakage support / proposed policy'),
         row(['3 · Sealed test','Train on oldest seasons, tune on later data, seal latest eligible completed season. Freeze exact split and power-derived minimum sample before test.','No split/power report · Not run'],('holdout',),'Holdout support / NFL design proposed'),
         row(['4 · Predictive quality','Strictly positive simultaneous lower bound for paired log-loss improvement over matched market; report Brier, calibration, n and coverage.','No predictions or intervals · Not run'],('logloss','brier'),'Metric definitions / threshold proposed'),
         row(['5 · Economics','Captured executable prices, costs and all settlement states; strictly positive simultaneous lower mean-return bound and predeclared drawdown tolerance.','No executable quotes or tolerance · Not run'],('repo','tails'),'Project policy / tail-risk context'),
         row(['6 · Selection control','Register every candidate. Proposed familywise alpha 0.05 across all primary claims; justify week-block resampling and power before the test.','No frozen family or inference · Not run'],('multiplicity',),'Error-control background / design proposed'),
         row(['7 · Stability','Frozen subgroup and degradation tolerances, prospective paper replication, missing-data/drift kill switch. No data-driven relaxation.','No tolerances or replication · Not run'],('holdout','repo'),'Generalization context / policy proposed')
     ]) + '<h2>Measuring skill without pretending to remove luck</h2><p>Report prediction quality and financial outcomes separately. A winning bet is not proof of skill; neither is a short positive-return run. Freeze the candidate family, compare matched targets, account for shared games/weeks and retain the untouched final test. The precise power study, resampling method and drift tolerances remain unimplemented and block eligibility.</p>')

page('leaderboard.html','Leaderboard','Performance must earn its rank.',
     'Four proposed tracks, matched targets, full disclosure. No strategy has passed validation. Empty metric cells mean unavailable—not zero.',
     table('Strategy leaderboard',['Track','Eligibility','Rank','Test n','Log-loss gain LCB','Net-return LCB','Reward'],[
         row([track,'Not run',None,None,None,None,None]) for track in ['G1 · Game single','P1 · Player prop','X1 · Cross-game parlay','S1 · Same-game combo']
     ]) + table('Competition policy',['Rule','Proposed treatment','State'],[
         row(['Ranking','Only all-gate-pass candidates within each matched-target track; rank by simultaneous lower confidence bound on log-loss improvement.','Not active'],('logloss','repo'),'Metric support / project rule'),
         row(['Ties','Lower Brier, then lower frozen model complexity; unresolved ties share rank. No cross-track global winner.','Proposed'],('brier','repo'),'Metric support / project rule'),
         row(['Reward','Hypothetical non-cash “research leader” badge per eligible track. None if no candidate qualifies.','No actual award']),
         row(['Funding and integrity','No sponsor, monetary pool or cash schedule. Publish pre-outcome submission hashes, all variants, exclusions and immutable test results.','Unfunded / not implemented'])
     ]))

page('correlations.html','Correlations','Dependence is not optional.',
     'No empirical NFL correlation values are available. The tested functions are descriptive math; no default zero, inferred sign or assumed independence is used.',
     table('Correlation register',['Predeclared pair / level','Required alignment','n','Pearson / phi','Interval','Status'],[
         row(['QB pass yards ↔ receiver yards / statistics','Same game/player IDs, official game-level yardage; not season aggregates.',None,None,None,'Unverified'],('nfl-stats','pearson'),'Input / formula context'),
         row(['QB passing-over ↔ receiver receiving-over / leg wins','Same game, exact thresholds, directions and settlement rules; exclude and disclose refunds.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Game total-over ↔ team player-over / leg wins','Same game and frozen lines; shared volume and game-script design needs testing.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Separate-game selections / leg wins','Predeclared same-week pairs with simultaneous executable quotes; never join arbitrary rows.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Strategy returns / economic outcomes','Aligned weeks, actual payout/cost/refund states; do not mix with stat or win correlations.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair')
     ]) + table('Dependence protocol',['Step','Rule','Implementation'],[
         row(['Paired statistic','Pearson measures linear dependence; for nonconstant binary legs use 0/1 Pearson (phi). Constant-leg correlation is undefined.','Descriptive arithmetic tested'],('pearson',),'Direct formula support / algebra'),
         row(['Two-leg joint price','P(A∩B)=p×q+rho×sqrt(p(1−p)q(1−q)); require max(0,p+q−1) ≤ joint ≤ min(p,q).','Algebra and feasibility checks tested'],('repo',),'Project Bernoulli algebra'),
         row(['Three or more legs','Pairwise correlations do not determine the full joint distribution. Need joint simulation or direct joint-event estimation and validation.','Not implemented'],('repo',),'Project mathematical limitation'),
         row(['Uncertainty','Publish window, eligible/excluded n, missingness and proposed week-block intervals; study dependence and power first. No interval if design invalid.','Not implemented'],('pearson','multiplicity'),'Inference context / NFL policy proposed')
     ]))

page('data.html','Data requirements','A trustworthy input contract.',
     'Source discovery is not dataset validation. No external NFL numbers have been copied into this site. The following is the acquisition contract, not a claim that inputs were acquired.',
     table('Data acquisition register',['Category','Minimum required fields','Evidence found','Readiness'],[
         row(['Outcomes and efficiency','Stable game/team/player IDs, season/type, official game-level scores, participation and stat units.','NFL publishes statistics by category and season. No game-level archive ingested.','Unverified dataset'],('nfl-stats',),'Publication verified / acquisition absent'),
         row(['Availability','Player ID, practice/game status, original publication timestamp, captured revision.','NFL injury page retrieved; blanks present. No historical point-in-time ledger.','Unverified dataset'],('nfl-injury',),'Publication verified / acquisition absent'),
         row(['Executable prices','Operator, jurisdiction, quote UTC, market/line, decimal price, stake availability, applicable settlement rules.','No qualifying official historical source obtained. NFL stats are not sportsbook odds.','Missing'],('repo','nfl-stats'),'Project gap / stats context only'),
         row(['Provenance','Source URL, retrieval UTC, original publication UTC, raw SHA-256, permissions and revision ID.','Source-reading register exists; no raw NFL observation archive or license confirmation.','Partial register only']),
         row(['Predictions and settlements','Code/config hash, training cutoff, issuance UTC, probabilities by state, official outcome link and settlement time.','No officially verified fitted model, forecast ledger or settled dataset; secondary analysis is separately flagged.','Missing'])
     ]) + '<h2>Fail-closed collection</h2><p>Do not infer a blank injury as healthy, a missing quote as an available price, a void as a loss, or a missing correlation as independence. Snapshot current inputs prospectively only after source permission and capture integrity are established. A credentialed feed has not been substituted or requested from you.</p>')

page('questions.html','Decision questions','Before a decision: what do we know?',
     'A review queue for decisions, missing evidence and practical next steps. “Answered” means answered by this repository’s inspected evidence—not that an NFL strategy is validated. Unknowns remain explicit; no user input or unsupported values are required.',
     '<div class="notice"><strong>Current decision: research-only, no strategy eligible.</strong><p>The work in this repository specifies methods and tests mathematical utilities, but does not establish NFL predictive skill, executable prices, measured player/defense effects, validated correlations, funded rewards or an automated data feed. The suggestions below are proposals for review; no model, data acquisition, wager or reward program is being silently enabled.</p></div>'
     + table('Decision questions and evidence gaps',['Decision area','Question to resolve','What is established now','Missing information / how to discover it','Decision status'],[
         row(['Line origination','Can Own9 publish defensible game or player-prop lines today?','A distribution-first design and pricing arithmetic exist. No verified fitted NFL probability model or numerical line exists in this dashboard.','Permissioned, timestamped historical NFL observations and executable prices; provenance and settlement rules; frozen forecast ledger. Validate before publishing any numeric line.','No — design only'],('repo',),'Project audit / not an empirical result'),
         row(['Player/defense injuries and replacements','Which starters are unavailable, and are second-, third- or fourth-choice replacements entering on offense or defense?','NFL’s injury page exposes player, position, injury, practice status and game status fields. This does not by itself establish depth order, participation, or historical pregame availability.','Discover and verify official dated team depth-chart/roster publications, inactive lists and game participation sources. Snapshot each version before kickoff; link player/team IDs; report explicit source-supported depth labels and replacement snaps. Never infer a blank as healthy or a depth rank from a name list.','No — source and history gap'],('nfl-injury','nfl-stats','repo'),'NFL fields verified / depth attribution unverified'),
         row(['Prices and settlement','Could a backtest reproduce a price that was actually available to a participant?','No qualifying historical executable quote archive is in the verified dashboard evidence. NFL statistics are not sportsbook prices.','Identify a permissioned provider/operator archive with timestamp, jurisdiction, market, line, decimal price, limits/availability and complete settlement rules; preserve raw capture and terms. If unavailable, no ROI or market-edge claim.','No — critical blocker'],('repo','nfl-stats'),'Project gap / source distinction'),
         row(['Skill rather than luck','What would qualify as evidence that a strategy beats a relevant baseline?','The proposal requires a frozen future holdout, proper scoring, family-wise error control and uncertainty; such tests can assess evidence, not remove chance.','Freeze hypotheses, matched market baseline, candidate family, power/design, folds and thresholds before evaluation. Record every trial, report all outcomes and replicate prospectively.','No — gates not run'],('holdout','brier','multiplicity','repo'),'Methods context / unrun policy'),
         row(['Parlays and player-prop combos','Are the legs dependent, and can the joint price be evaluated?','Pearson/phi and joint-probability arithmetic are documented; no verified aligned NFL sample, coefficient or confidence interval is available. Pairwise correlation alone does not define a 3+ leg joint distribution.','Build paired event/settlement IDs with leg definitions, thresholds, quote times, pushes/voids and shared-game/week structure. Estimate joint calibration and uncertainty on held-out data; do not assume independence.','No — no measured NFL dependence'],('pearson','repo'),'Formula support / no NFL estimate'),
         row(['Competition and rewards','What can the leaderboard reward without mistaking variance for skill?','Tracks and gates are proposals. No eligible entry, sponsor, cash pool or actual award is recorded.','First freeze comparable targets, public scoring rules, anti-selection policy, sample/power floor, entry hashes and tie rules. Start with non-cash recognition only if all gates pass; cash requires separately verified funding and rules.','No — no funded program'],('repo','multiplicity'),'Project policy / not funded'),
         row(['Automatic operation','Can the requested system collect, validate and publish everything without user input?','Static pages and local checks exist; no permissioned scheduled NFL/odds ingestion or source credential/feed is established.','Before automation, confirm source terms, stable IDs, timestamp/version retention, failure alerts, missing-data behavior and reproducible deployment. Do not invent credentials, scrape against terms, or silently fill gaps.','No — pipeline absent'],('pages','repo'),'Hosting context / acquisition absent'),
         row(['Permission and scope','May the required source data be stored and reused for this analysis/site?','No license/permission determination for an odds archive or all historical data is recorded in the verified evidence set.','Review the actual source/provider terms and retention/redistribution permissions before acquisition; record the exact applicable document, date and decision. Until then, do not assume rights.','Unresolved — verify first'],('repo',),'Project evidence gap / no legal conclusion')
     ]) + table('Improvement suggestions — review before implementation',['Priority','Suggestion / candidate paths','Recommended path','Why / evidence gate'],[
         row(['1 · Foundation','A. Continue with ad-hoc files. B. Create a versioned source and permission register before collection.','Choose B: specify stable IDs, UTC timestamps, source publication/retrieval times, raw hashes, revision history, units, settlement rules and documented data-use permission.','Without provenance, later scoring and source review cannot be reproduced. Current repository records no qualifying paired dataset or permissioned quote archive.'],('repo',),'Recommended proposal / current gap'),
         row(['2 · Availability','A. Treat injury labels as a binary healthy/unhealthy signal. B. Preserve dated injury, depth, inactive and participation evidence separately.','Choose B: build a time-stamped roster/availability timeline and only attach an ordinal replacement label when an official dated depth source explicitly supports it; track actual participation separately.','The official injury page has practice/game status fields, but the verified source scope does not provide a historical depth chart or prove replacement snaps. Missing means unknown, not healthy.'],('nfl-injury','nfl-stats','repo'),'NFL publication fields / unverified depth history'),
         row(['3 · Prices','A. Backtest against closing-line estimates. B. Use timestamped executable quotes with rules.','Choose B; if no permissioned archive is available, restrict work to probability forecasting and make no return/profit claim.','No qualifying price archive is established; a proxy price cannot stand in for an executable quote.'],('repo',),'Proposal / archive absent'),
         row(['4 · Validation','A. Rank by win rate or recent ROI. B. Pre-register a matched baseline and sealed, uncertainty-aware gates.','Choose B: size sample by a documented power/design study, preserve the final holdout, correct for all tried candidates, and require future paper replication.','Win rate and short runs alone do not show skill. Existing statistical references support method concepts, not an NFL strategy’s success.'],('holdout','brier','multiplicity','repo'),'Method support / NFL thresholds still unset'),
         row(['5 · Combos','A. Multiply marginal probabilities. B. Estimate aligned joint-event probabilities and compare the actual combo quote.','Choose B only after paired leg and settlement history exists; distinguish cross-game from same-game combos and retain full multi-leg settlement states.','No verified NFL correlations or joint calibration exist; pairwise statistics alone cannot identify every 3+ leg joint distribution.'],('pearson','repo'),'Mathematical design / evidence absent'),
         row(['6 · Leaderboard','A. Offer cash rewards immediately. B. Publish transparent, separate tracks and delay awards until every gate and funding rule is met.','Choose B: keep rewards blank now; if desired later, start with non-cash recognition, fixed scoring/tie rules and an independently checked eligibility record.','No sponsor, pool or eligible strategy is evidenced. This proposal prevents a leaderboard rank from implying proven skill or funded rewards.'],('repo','multiplicity'),'Project proposal / no award authorized')
     ]) + '<h2>Review outcome</h2><p>Current recommended path: keep the site as a no-wager research framework; prioritize source/permission discovery and a prospective timestamped data contract, then freeze validation design. Do not fit or rank a strategy until the data and gates are satisfied. No manual action is needed to see this status; unresolved external permissions, licensed quote access and empirical evidence cannot be manufactured by this session.</p><p>Implementation changes beyond this review page should be selected only after the corresponding source and validation gates are documented. See <a href="flags.html">Flagged for Review</a> for the open limitations and <a href="data.html">Data requirements</a> for the minimum input contract.</p>')


def table(title, headers, rows):
    output = f'<h2>{e(title)}</h2><div class="table-wrap"><table><caption class="sr-only">{e(title)}</caption><thead><tr>'
    output += ''.join(f'<th scope="col">{e(h)}</th>' for h in [*headers, 'Evidence / scope'])
    output += '</tr></thead><tbody>'
    for i, (cells, refs, kind) in enumerate(rows,1):
        output += f'<tr id="{e(title.lower().replace(" ","-"))}-{i}">'
        for j,c in enumerate(cells):
            tag = 'th scope="row"' if j == 0 else 'td'
            close = 'th' if j == 0 else 'td'
            output += f'<{tag}>{e(str(c)) if c is not None else ""}</{close}>'
        links = ' · '.join(f'<a href="{e(SOURCES[r]["url"],quote=True)}">{e(SOURCES[r]["publisher"])} ↗</a>' for r in refs)
        output += f'<td><span class="evidence-kind">{e(kind)}</span>{links}</td></tr>\n'
    return output + '</tbody></table></div>'


def row(cells, refs=('repo',), kind='Project record'):
    return cells, refs, kind


def page(file, label, title, intro, content):
    PAGES[file] = (label,title,intro,content)


page('index.html','Overview','Evidence first.\nAn edge must be earned.',
     'An NFL line-origination lab for game singles, player props and joint bets. Built to test skill—not reward a lucky streak.',
     '''<div class="notice"><strong>Research framework · no validated strategies</strong><p>No verified historical executable odds or point-in-time paired dataset was obtained. NFL lines, measured correlations, test scores and cash rewards are intentionally blank. No wagering is enabled.</p></div>
<div class="cards"><a href="decision.html"><span>01 / DECIDE</span><b>Decision brief</b><p>16 open decisions, defaults and stopping rules</p></a><a href="questions.html"><span>02 / ASK</span><b>Questions &amp; answers</b><p>22 questions: answered, open, unpublished</p></a><a href="availability.html"><span>03 / AVAILABILITY</span><b>Who actually started</b><p>Official lineups, verified changes</p></a><a href="suggestions.html"><span>04 / REVIEW</span><b>Suggestions</b><p>Scored, falsifiable, choose before building</p></a><a href="strategies.html"><span>05 / HYPOTHESES</span><b>Signal registry</b><p>Singles, props &amp; joint models</p></a><a href="validation.html"><span>06 / DISCIPLINE</span><b>Seven evidence gates</b><p>Fail closed. Publish all trials.</p></a><a href="correlations.html"><span>07 / DEPENDENCE</span><b>Correlation lab</b><p>Paired evidence, not assumptions</p></a><a href="leaderboard.html"><span>08 / COMPETITION</span><b>Evidence leaderboard</b><p>No eligible entries, no awards</p></a></div><div class="cards"><a href="injuries.html"><span>09 / AVAILABILITY</span><b>Injuries & depth</b><p>Week 10 2026 verified snapshot</p></a><a href="data.html"><span>10 / INPUTS</span><b>Data requirements</b><p>Acquisition contract, fail closed</p></a><a href="audit.html"><span>11 / RECORDS</span><b>Repository audit</b><p>Implementation and integration log</p></a><a href="flags.html"><span>12 / TRANSPARENCY</span><b>Flagged for Review</b><p>Published irregularities, F01-F21</p></a></div>'''
     + table('Executive summary',['Decision area','Finding','Disposition'],[
         row(['Originate NFL lines','A distribution-first design is specified; tested pricing primitives exist. No officially verified fitted NFL probability model or numerical line is available in this dashboard.','Implemented math / model not implemented']),
         row(['Useful signals','Opponent-adjusted efficiency, pace, participation and shared game script are hypotheses; no direction, effect size or profitability is asserted.','Research proposals'],('nfl-stats','nfl-injury'),'Context only / proposed'),
         row(['Skill versus luck','Use sealed future periods, proper scoring, multiplicity control and uncertainty. These can test evidence of skill, not eliminate chance.','No skill certification'],('holdout','brier','multiplicity'),'Method support / policy proposed'),
         row(['Correlation','No verified aligned sample was obtained. Descriptive Pearson/phi code is tested only on synthetic examples.','Unverified NFL values'],('pearson','repo'),'Formula support / project record'),
         row(['Competition rewards','Separate target-matched tracks and hypothetical recognition badges are proposed. No sponsor, cash pool or awards exist.','No funded program']),
         row(['Availability tracking','Two official Game Books show four of four published starting elevens changed between Week 9 and Week 10 for WAS and NYG, and one starting slot has a fully documented replacement. No official depth tier is available, so second/third/fourth-string labels remain blank.','Verified change / tier unpublished'],('nfl-gamebook-w10','nfl-gamebook-w9-lar-was','nfl-gamebook-w9-nyg-phi'),'Direct publisher / three game books'),
         row(['Decisions and questions','16 decisions carry a default and a predeclared stopping rule. 22 questions are split into 12 answered, 8 open and 2 fields the publisher does not release.','Published registers'],
             ('repo',),'Project record'),
         row(['Suggested improvements','16 suggestions scored on decision impact and evidence cost. 12 accepted and carried by a decision, 2 deferred, 2 blocked on a missing archive or licence.','Reviewable queue'],('repo',),'Project record'),
         row(['Executive recommendation','Continue as a paper-research lab. Missing provenance, prices or validation blocks eligibility—not publication of limitations.','No bets recommended'])
     ]) + '<p class="download">Read the <a href="questions.html">decision questions &amp; improvement suggestions</a> register, the <a href="docs/RESEARCH_SPEC.md">full research specification</a>, the <a href="decision.html">decision brief</a> and the <a href="audit.html">repository audit</a>. Every empirical gap appears on <a href="flags.html">Flagged for Review</a>, every proposed change is queued on <a href="suggestions.html">Suggestions</a>, and the earlier <a href="decisions-questions.html">decision questions register</a> is preserved with its own recommended paths.</p>'
     + table('Related sections in this repository',['Section','Contents','Publisher / session record','Integration state'],[
         row(['Additive dashboard','Independent source-linked lab with pricing primitives and 11 gates; publishes at /Own9/site/.','Repository record','Live subsite — linked, not merged'],('repo',),'Project record'),
         row(['Strict-source lab','Additive strict-lab research section with published evidence flags F01-F12.','Repository record','Live subsite — linked, not merged'],('repo',),'Project record'),
         row(['Signal research','Secondary-source pipeline: 15 strategies, walk-forward own-line model; findings flagged uncertified.','Repository record','Live subsite — linked, not adopted'],('repo',),'Project record'),
         row(['Own9 research lab','Separate pipeline and 12-page dashboard; empirical figures flagged unverified.','Repository record','Live subsite — linked, not adopted'],('repo',),'Project record'),
         row(['Release checks','Independent structural/deployment review reports and snapshots.','Repository record','Live subsite — linked'],('repo',),'Project record'),
         row(['Independent audit','Five-page official-source audit of the original 28-row dashboard, integrated from PR #18 (stale-session takeover, 2026-11-14).','Repository record','Live subsite — linked'],('repo',),'Project record')
     ]))

page('strategies.html','Strategies','The signal registry.',
     'Predeclared research candidates. These are designs to test, not discovered edges or recommendations. Contextual references do not endorse a strategy.',
     table('Candidate strategies',['ID / track','Proposed signal and model','Required ablation / falsification','State'],[
         row(['G1 · Game single','Opponent-adjusted past efficiency, pace and availability → regularized joint score distribution → moneyline, spread and total.','Remove efficiency, pace and availability one at a time; compare frozen baseline on later weeks.','Unvalidated'],('nfl-stats','nfl-injury'),'Official input categories / proposal'),
         row(['P1 · Player prop','Participation × opportunities × conditional efficiency; separate count and yardage distributions.','Exposure-only baseline; remove availability adjustments; audit missing participation and player-role changes.','Unvalidated'],('nfl-stats','nfl-injury'),'Official input categories / proposal'),
         row(['X1 · Cross-game parlay','Common-week latent scenarios → joint win probability. Use actual combo quote, not multiplied marginal odds.','Compare joint model with independence baseline; test held-out joint-event calibration.','Unvalidated'],('pearson','repo'),'Dependence background / proposal'),
         row(['S1 · Same-game prop combo','Shared plays, game script, team pass/rush and target allocation → joint player outcomes with accounting constraints.','Remove shared effects; check feasible combinations, joint calibration and every settlement rule.','Unvalidated'],('nfl-stats','pearson'),'Input / dependence context only'),
         row(['A1 · Selective abstention','Withhold when data, quoted price or model support is missing; freeze any edge cutoff before the final test.','Publish abstention count and coverage; evaluate the complete decision rule, not selected winners.','Unvalidated'],('holdout','repo'),'Overfit support / policy proposed')
     ]) + table('Line origination contract',['Market / calculation','Definition','Limit'],[
         row(['Home spread','With M = home score − away score and signed home handicap h, cover = P(M+h>0); push = P(M+h=0).','A fair handicap is not generally the mean margin. Numerical line unavailable.'],('repo',),'Project mathematical specification'),
         row(['Total / prop over','Sum mass strictly above the quoted threshold; retain equality as a separate push state.','Must specify overtime, participation and void rules. No numerical threshold inferred.'],('repo',),'Project mathematical specification'),
         row(['Fair decimal / expected return','Dfair = 1 + Ploss/Pwin. Net EV per unit = Pwin×(D−1) − Ploss − cost, with full refunds earning zero.','Undefined if Pwin=0; reduced-leg payouts require a full state model. Algebra tested, not an edge.'],('repo',),'Project algebra / unit tested'),
         row(['Market baseline','Normalize inverse decimal prices over every mutually exclusive exhaustive no-push outcome.','Proportional de-vig is a declared comparison convention, not verified true probability.'],('repo',),'Project baseline convention')
     ]))

page('validation.html','Validation','Seven gates. No shortcuts.',
     'Proposed acceptance policy. Every gate is mandatory; a missing value is not a pass. Unit tests validate software arithmetic—not NFL skill.',
     table('Validation gates',['Gate','Acceptance requirement','Artifact / current state'],[
         row(['1 · Provenance','All evaluated records have official outcome URLs, IDs, units, source timestamps, raw hashes and rule snapshots; quarantine missing required records.','No qualifying dataset · Not run'],('nfl-stats','repo'),'Data context / proposed policy'),
         row(['2 · Point in time','Features and quotes available before issuance and kickoff; freeze forecasts; no same-game fold leakage.','No forecast/quote ledger · Not run'],('holdout','repo'),'Leakage support / proposed policy'),
         row(['3 · Sealed test','Train on oldest seasons, tune on later data, seal latest eligible completed season. Freeze exact split and power-derived minimum sample before test.','Blocked by decision D-10 · Not run'],('holdout','repo'),'Holdout support / dependency named'),
         row(['4 · Predictive quality','Strictly positive simultaneous lower bound for paired log-loss improvement over matched market; report Brier, calibration, n and coverage.','No predictions or intervals · Not run'],('logloss','brier'),'Metric definitions / threshold proposed'),
         row(['5 · Economics','Captured executable prices, costs and all settlement states; strictly positive simultaneous lower mean-return bound and predeclared drawdown tolerance.','No executable quotes or tolerance · Not run'],('repo','tails'),'Project policy / tail-risk context'),
         row(['6 · Selection control','Register every candidate. Proposed familywise alpha 0.05 across all primary claims; justify week-block resampling and power before the test.','No frozen family or inference · Not run'],('multiplicity',),'Error-control background / design proposed'),
         row(['7 · Stability','Frozen subgroup and degradation tolerances, prospective paper replication, missing-data/drift kill switch. No data-driven relaxation.','No tolerances or replication · Not run'],('holdout','repo'),'Generalization context / policy proposed')
     ]) + '<h2>Measuring skill without pretending to remove luck</h2><p>Report prediction quality and financial outcomes separately. A winning bet is not proof of skill; neither is a short positive-return run. Freeze the candidate family, compare matched targets, account for shared games/weeks and retain the untouched final test. The precise power study, resampling method and drift tolerances remain unimplemented and block eligibility.</p>')

page('leaderboard.html','Leaderboard','Performance must earn its rank.',
     'Four proposed tracks, matched targets, full disclosure. No strategy has passed validation. Empty metric cells mean unavailable—not zero.',
     table('Strategy leaderboard',['Track','Eligibility','Rank','Test n','Log-loss gain LCB','Net-return LCB','Reward'],[
         row([track,'Not run',None,None,None,None,None]) for track in ['G1 · Game single','P1 · Player prop','X1 · Cross-game parlay','S1 · Same-game combo']
     ]) + table('Competition policy',['Rule','Proposed treatment','State'],[
         row(['Ranking','Only all-gate-pass candidates within each matched-target track; rank by simultaneous lower confidence bound on log-loss improvement.','Not active'],('logloss','repo'),'Metric support / project rule'),
         row(['Ties','Lower Brier, then lower frozen model complexity; unresolved ties share rank. No cross-track global winner.','Proposed'],('brier','repo'),'Metric support / project rule'),
         row(['Reward','Hypothetical non-cash “research leader” badge per eligible track. None if no candidate qualifies.','No actual award']),
         row(['Funding and integrity','No sponsor, monetary pool or cash schedule. Publish pre-outcome submission hashes, all variants, exclusions and immutable test results.','Unfunded / not implemented'])
     ]) + table('Live-to-paper demotion gate',['Trigger','Automatic action','Re-entry condition / state'],[
         row(['Integrity or operational breach: invalid/missing price or result provenance, corrupted or stale required inputs, settlement mismatch, unauthorized strategy version, or a frozen exposure/data kill-switch trip.','Immediately stop new live issuance; freeze the affected version and evidence; set status to Paper pending incident review. Do not wait for a performance sample.','Paper immediately. Resume only after the incident is resolved, the version and data are re-audited, and all affected entry gates pass again.'],('repo',),'Proposed project control; no live deployment'),
         row(['Scheduled validation: any mandatory entry gate is no longer demonstrated for the locked strategy version. In particular, the predeclared predictive-quality or net-return lower bound is not strictly positive, or drift/stability fails. Missing/invalid evidence counts as not passing.','Automatically demote to Paper at that checkpoint; retain the full monitoring window, exclusions, and trigger record. No discretionary threshold relaxation.','Use the same gate definitions as entry. Monitoring window, minimum n, confidence procedure/alpha, review cadence, stale-data tolerance, and exposure cap are not yet specified; live activation is blocked until frozen.'],('repo','logloss'),'Proposed project control; numeric operating settings unresolved'),
         row(['Re-entry after a performance demotion','No immediate flip back to live when a short run improves. Keep the failed strategy version in Paper.','Full requalification against all seven frozen gates on untouched prospective evidence; any changed model, feature, or rule is a new version and requires a new sealed evaluation.','Not authorized / not implemented'],('repo','holdout'),'Proposed project control; no strategy is live')
     ]) + '<p class="disclaimer"><strong>Gate status: defined as a fail-closed policy, not operationally active.</strong> There is no live strategy in this repository. The site contains no validated NFL performance evidence, and the operating settings listed above must be frozen before any live eligibility could be considered.</p>')

page('correlations.html','Correlations','Dependence is not optional.',
     'No empirical NFL correlation values are available. The tested functions are descriptive math; no default zero, inferred sign or assumed independence is used.',
     table('Correlation register',['Predeclared pair / level','Required alignment','n','Pearson / phi','Interval','Status'],[
         row(['QB pass yards ↔ receiver yards / statistics','Same game/player IDs, official game-level yardage; not season aggregates.',None,None,None,'Unverified'],('nfl-stats','pearson'),'Input / formula context'),
         row(['QB passing-over ↔ receiver receiving-over / leg wins','Same game, exact thresholds, directions and settlement rules; exclude and disclose refunds.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Game total-over ↔ team player-over / leg wins','Same game and frozen lines; shared volume and game-script design needs testing.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Separate-game selections / leg wins','Predeclared same-week pairs with simultaneous executable quotes; never join arbitrary rows.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Strategy returns / economic outcomes','Aligned weeks, actual payout/cost/refund states; do not mix with stat or win correlations.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair')
     ]) + table('Dependence protocol',['Step','Rule','Implementation'],[
         row(['Paired statistic','Pearson measures linear dependence; for nonconstant binary legs use 0/1 Pearson (phi). Constant-leg correlation is undefined.','Descriptive arithmetic tested'],('pearson',),'Direct formula support / algebra'),
         row(['Two-leg joint price','P(A∩B)=p×q+rho×sqrt(p(1−p)q(1−q)); require max(0,p+q−1) ≤ joint ≤ min(p,q).','Algebra and feasibility checks tested'],('repo',),'Project Bernoulli algebra'),
         row(['Decision gate','A Fisher-z interval is formed on the paired outcome. Only a verdict whose whole interval clears a predeclared deadband may enter a joint price; any other verdict returns no price at all.','Implemented and unit-tested on synthetic data'],('pearson','repo'),'Formula support / project implementation'),
         row(['Why not independence','Multiplying marginals asserts rho = 0. The gate exists so that a blank joint price is a true statement about missing evidence rather than a confident wrong number.','Policy implemented in engine/core.py'],('repo',),'Project policy'),
         row(['Three or more legs','Pairwise correlations do not determine the full joint distribution. Need joint simulation or direct joint-event estimation and validation.','Not implemented'],('repo',),'Project mathematical limitation'),
         row(['Uncertainty','Publish window, eligible/excluded n, missingness and proposed week-block intervals; study dependence and power first. No interval if design invalid.','Not implemented'],('pearson','multiplicity'),'Inference context / NFL policy proposed')
     ]))

page('data.html','Data requirements','A trustworthy input contract.',
     'Source discovery is not dataset validation. No external NFL numbers have been copied into this site. The following is the acquisition contract, not a claim that inputs were acquired.',
     table('Data acquisition register',['Category','Minimum required fields','Evidence found','Readiness'],[
         row(['Outcomes and efficiency','Stable game/team/player IDs, season/type, official game-level scores, participation and stat units.','NFL publishes statistics by category and season. No game-level archive ingested.','Unverified dataset'],('nfl-stats',),'Publication verified / acquisition absent'),
         row(['Availability','Player ID, practice/game status, original publication timestamp, captured revision.','NFL injury page retrieved; blanks present. Two official Game Books give a verified two-week starting lineup diff for WAS and NYG.','Partial: one club-game pair'],('nfl-injury','nfl-gamebook-w10'),'Publication verified / narrow coverage'),
         row(['Executable prices','Operator, jurisdiction, quote UTC, market/line, decimal price, stake availability, applicable settlement rules.','No qualifying official historical source obtained. NFL stats are not sportsbook odds.','Missing'],('repo','nfl-stats'),'Project gap / stats context only'),
         row(['Provenance','Source URL, retrieval UTC, original publication UTC, raw SHA-256, permissions and revision ID.','Source-reading register exists; no raw NFL observation archive or license confirmation.','Partial register only']),
         row(['Predictions and settlements','Code/config hash, training cutoff, issuance UTC, probabilities by state, official outcome link and settlement time.','No officially verified fitted model, forecast ledger or settled dataset; secondary analysis is separately flagged.','Missing'])
     ]) + '<h2>Fail-closed collection</h2><p>Do not infer a blank injury as healthy, a missing quote as an available price, a void as a loss, or a missing correlation as independence. Snapshot current inputs prospectively only after source permission and capture integrity are established. A credentialed feed has not been substituted or requested from you.</p>')

page('sources.html','Sources','The evidence register.',
     'Official publisher and reference pages read between 04 Nov and 14 Nov 2026, each with the precise claim it supports and its limits. A retrieved page is not a verified NFL model, and source contents can change.',
     table('Official source review',['Reference ID','Supported scope','Limits / evidence state','Checked UTC date'],[
         row([s['id'],s['supports'],s['scope']+' ['+s['status']+']',s['checked']],(s['id'],),'Direct publisher / checked scope') for s in SOURCES.values()
     ]) + '<p>Each row throughout the dashboard links to a publisher reference or this project’s primary repository record. Labels distinguish direct support, contextual background, mathematical specification and project proposals. The <a href="evidence/sources.json">machine-readable manifest</a> records the same scope. References do not endorse betting strategies.</p>')

page('audit.html','Repository audit','Review the implementation, too.',
     'Two audits are recorded. The original integration read all 11 tracked files at commit 71236ddd74208838537d87ecfe722e578671f69f. This session re-read the root generator, both verifiers, the source manifest, the engine and the evidence files, then added three official documents and four new page scopes.',
     table('Starting checkout audit',['File scope','Finding after reading contents','Action / status'],[
         row(['COORDINATION.md','Earlier session already built a framework; its old “initial README only” statement refers to an older checkout.','Preserved history, recorded handoffs and board conflicts.']),
         row(['README.md','Accurately called the old site a framework, but no executable research model existed.','Document actual math versus remaining acquisition/model gaps.']),
         row(['tools/build.py','Generated static proposals; broad NIST references did not directly substantiate every gate.','Replace generic labels with scoped evidence and explicit project policies.']),
         row(['tools/check.py','Checked local link targets and allowed source hosts only. Could not prove claim support or external reachability.','Replace with stronger structural/freshness checks; do not call this factual verification.']),
         row(['index.html / strategies.html / validation.html','Generated research concepts, not measured NFL results. Initial-repo claim needed historical context.','Re-render from reviewed specifications; no empirical values added.']),
         row(['leaderboard.html / flags.html','Empty placeholder metrics correctly withheld; no tested rank or funded reward.','Preserve blanks and add explicit validation blockers.']),
         row(['style.css','Responsive static CSS, no external scripts, trackers or data capture.','Improve current-page navigation, keyboard access, search and mobile table handling.'])
     ]) + table('Integration review',['New scope','Checks performed / acceptance','Limitation'],[
         row(['research/metrics.py / tests/','Synthetic arithmetic tests cover pricing, scoring, phi/joint feasibility, missing/nonfinite rejection and fail-closed eligibility.','No fitted model or strategy backtest.']),
         row(['evidence/ / docs/','Every manifest entry manually read in its stated scope. Full research specification separates proposals from facts.','No independent numerical NFL observation verification.']),
         row(['Site generator / checker / CI','Deterministic generation, local asset/fragment checks, all table rows have known sources, blank empirical metrics and Python test suite.','Remote reachability is not established by local checks; no automated claim-entailment certification.']),
         row(['evidence/lineups/ · evidence/availability/','Both files read field by field against three official Game Books and the Week 10 report. A fail-closed validator rejects a filled depth tier, a false retained/in/out claim, a wrong starter count, and an unknown status.','Two-week coverage only; no season archive.']),
         row(['research/suggestions.json · decision-register.json · decision-brief.json','Every row checked for a falsification statement, a decision reference, a stopping rule, a blocker or a source. 12 answered questions carry a publisher link; the two non-publisher bases carry an explicit note.','Advisory content; verified for structure and sourcing, not for truth of an opinion.']),
         row(['engine/core.py · engine/availability.py · engine/registers.py','New dependence gate exercised on synthetic values only. Interval width shrinks with n; a zero-straddling interval refuses to price a joint; infeasible correlations raise. 79 tests pass.','No NFL correlation is measured or implied anywhere.'])
     ]) + '<p>Later merged PR #6 added analysis/, data/raw/ and research/ pages. Those inherited empirical claims are not line-by-line certified by this session; see F12 on Flagged for Review. Audit references point to the official project repository as the primary record for implementation findings—not to unrelated NFL documentation. See <a href="docs/RESEARCH_SPEC.md">the full specification</a> for what remains unimplemented.</p>')

page('flags.html','Flagged for Review','Uncertainty, in plain sight.',
     'Published irregularities do not block this research site. They do block empirical claims, leaderboard eligibility and any reward. No manual input is required to view the findings.',
     table('Review register',['ID / severity','Finding','Required evidence / disposition','State'],[
         row(['F01 · Critical','No official historical executable odds archive obtained.','Capture verifiable operator quotes and settlement rules; never synthesize missing prices.','Unverified']),
         row(['F02 · Critical','No officially verified point-in-time paired NFL dataset, fitted model or forecasts.','Build permissioned ingestion and provenance before fitting or assessing signals.','Not implemented'],('nfl-stats','nfl-injury','repo'),'Publisher context / project gap'),
         row(['F03 · Critical','No measured correlations, confidence intervals or joint calibration.','Acquire aligned observations; freeze leg definitions and valid dependence-aware inference.','Unverified'],('pearson','repo'),'Formula context / project gap'),
         row(['F04 · Critical','No officially verified backtest, power study, sealed test, drift tolerances or prospective replication.','All seven gates fail closed. No strategy is certified.','Not run'],('holdout','repo'),'Method support / project gap'),
         row(['F05 · Review','Official source links alone do not prove the strategy or a row’s proposal.','Scope labels retained. NFL/NIST/SciPy/sklearn pages do not endorse an NFL edge.','Published limitation']),
         row(['F06 · Review','No funded competition, sponsor, monetary rewards or actual badges awarded.','Non-cash recognition rules are hypothetical; leave cash amounts blank.','Unverified']),
         row(['F07 · Limitation','Luck cannot be removed; validation is not a guarantee of future profit.','Probabilistic forecasting and held-out evidence, not deterministic winning claims.','No promise made'],('holdout','brier'),'Uncertainty context / project limitation'),
         row(['F08 · Review','Current injury and statistics pages cannot establish what was known before historical games.','Preserve timestamped original captures and revisions; do not infer missing health fields.','Unverified historical inputs'],('nfl-injury','nfl-stats'),'Current publications / historical limitation'),
         row(['F09 · Review','Source availability and row claim support are not proved by the site checker.','Manifest records pages actually read; local checks are structural only.','Published limitation']),
         row(['F10 · Limitation','Pricing functions support full refunds, not reduced-leg payouts, dead heats or every operator rule.','Use a complete payout-state model before evaluating affected parlays.','Unsupported states rejected by scope']),
         row(['F11 · Review','Prior sessions left deployment notes and broad contextual citations.','PR #2 corrections preserved; this session re-scopes sources and records its own deploy separately.','Historical context preserved']),
         row(['F12 · Review','Merged PR #6 adds a separate secondary-data analysis subtree; its PR reports only two completed scores officially cross-checked.','Inherited files preserved, but numerical findings not certified or adopted by this dashboard. Official row-level verification and rights remain unresolved.','Unverified inherited research']),
         row(['F13 · Review','No official depth chart could be obtained and no first/second/third/fourth-string designation was found, so the requested backup-tier tracking cannot be satisfied as specified.','Verified substitution: changed starters from official Game Books, with the tier field left blank and labelled unpublished. Published on the availability page.','Field unavailable — substituted'],('nfl-roster','nfl-gamebook-w10'),'Direct publisher / absence verified'),
         row(['F14 · Review','Three of four verified Week 10 lineup changes have no published cause, and six of seven Giants inactives carried no injury designation.','Do not infer cause from the injury report when the report itself shows no designation. Cause stays null.','Cause unpublished'],('nfl-injury','nfl-gamebook-w10'),'Direct publisher / two documents'),
         row(['F15 · Review','Official Game Books carry an NFL copyright notice restricting use.','Short excerpts only, originals linked, no republication. Formal permission not obtained.','Rights unresolved'],('nfl-gamebook-w10','nfl-capsules-pdf'),'Publisher terms'),
         row(['F16 · Review','Availability coverage is two clubs across two consecutive weeks only. Each week-over-week block compares one club against a different opponent, which is the correct comparison for a lineup diff but cannot separate a lineup effect from an opponent effect.','Coverage is a two-week demonstration, not a season dataset. Any generalisation is blocked on the archive decision D-11.','Narrow coverage'],('nfl-gamebook-w9-lar-was','nfl-gamebook-w9-nyg-phi','nfl-gamebook-w10'),'Direct publisher / three game books'),
                  row(['F17 · Review','The Washington club depth-chart route on nfl.com returns an NFL 404. A single-route miss is not proof that no depth chart exists anywhere.','Stated only as far as verified: this project could not obtain a depth chart from the league site. Depth tiers stay blank.','Negative result recorded'],('nfl-depth-chart-404',),'Direct publisher / 404 route'),
row(['F18 · Critical','No executable historical price or point-in-time quote ledger exists, so no line, correlation, joint probability or return on this site can be priced.','Acquire a licensed quote source or run a forward capture. Every affected cell stays blank.','Unverified'],('repo','dk-markets'),'Project gap / operator rule context'),
         row(['F19 · Review','Official club depth charts DO exist on team sites — KC, SEA and DET charts with first/second/third/fourth-string columns were retrieved 2026-11-14, narrowing the route-scoped negative result in F17; every club chart is self-labeled "unofficial" by the club itself.','Depth-slot attributions on injuries.html cite both the league report and the club chart and stay caveated; charts are not certified game-day depth; the other 29 clubs were not retrieved this session.','Positive finding / caveated'],('chiefs-depth','seahawks-depth','lions-depth','nfl-depth-chart-404'),'Direct publisher / supersedes F17 for three clubs'),
         row(['F20 · Review','Cross-source conflict: DET S Kerby Joseph carries an Out game status on the Week 10 2026 league report but is absent from the club chart\'s safety rows (both retrieved 2026-11-14).','Conflicting official publications must be surfaced, not reconciled; no replacement is inferred for that slot. Similar conflicts may exist for clubs whose charts were not retrieved.','Unresolved — manual review'],('nfl-injury-w10','lions-depth','repo'),'Cross-source conflict / withheld'),
         row(['F21 · Review','The injuries.html Week 10 snapshot is a single point-in-time retrieval (160 Out/Doubtful/Questionable entries across 14 games): the report publishes no revision timestamp, roster assignments were not cross-verified against a second independent official source, and no historical point-in-time injury/depth archive exists in verified evidence.','Snapshot rows are tied to retrieval UTC 2026-11-14 and must be refreshed before lineup lock; F02/F08 stand. Injury data confers no validated predictive edge.','Snapshot dated / archive missing'],('nfl-injury-w10','repo'),'Snapshot limitation / project gap')
     ]) + '<p>Independent earlier-baseline technical report: <a href="release-checks/index.html">release quality review</a>. Its stored five-page / 28-row snapshot predates this nine-page integration; it is not a current factual or deployment certification.</p><p>Separate inherited, uncertified analysis: <a href="https://github.com/sassnarep3-star/Own9/pull/6">PR #6 and its stated evidence limitations</a>; <a href="research/flagged.html">its separate review register</a>. Its numerical findings are not adopted by this dashboard.</p>'
     + '<p>Review registers and reports in linked subsites (each governed by its owning session\'s scope): <a href="site/review.html">site/ review (F01-F13)</a> · <a href="strict-lab/flags.html">strict-lab/ flags (F01-F12)</a> · <a href="research/flagged.html">research/ flagged (F1-F8)</a> · <a href="own9-research/flags.html">own9-research/ flags</a> · <a href="release-checks/index.html">release-checks/ report</a> · <a href="release-checks/expanded-review.html">expanded source-policy review</a> · <a href="independent-audit/flags.html">independent-audit/ flags</a>. Subsite findings are published by their owning sessions; this root dashboard neither certifies nor adopts them.</p>')




def _ranked():
    return sorted(enumerate(sorted(SUGGESTIONS['suggestions'], key=impact_rank), 1), key=lambda t: t[0])


def _suggestion_summary():
    counts = {k: sum(1 for x in SUGGESTIONS['suggestions'] if x['status'] == k)
              for k in ('accepted','deferred','blocked_on_evidence','proposed','rejected')}
    cells = ''.join(f'<div><b>{counts[k]}</b><span>{STATE_LABEL[k]}</span></div>'
                    for k in ('accepted','deferred','blocked_on_evidence','proposed','rejected'))
    return f'<div class="stats">{cells}</div>'


def _counts_strip():
    counts = {k: sum(1 for q in QUESTIONS['questions'] if q['state'] == k)
              for k in QUESTIONS['states']}
    cells = ''.join(f'<div><b>{counts[k]}</b><span>{STATE_LABEL[k]}</span></div>' for k in QUESTIONS['states'])
    return f'<div class="stats">{cells}</div>'


def _standing_constraints():
    items = ''.join(f'<li>{e(x)}</li>' for x in BRIEF['standing_constraints'])
    return f'<h2>Standing constraints</h2><ul class="rules">{items}</ul>'


def _lineup_tables():
    out = ['<h2>Starting-lineup comparison, Week 9 to Week 10</h2>',
           '<p>Each block lists the eleven players the NFL printed as starters for that side of the ball in the official Game Book. Order inside a block carries no meaning beyond the published print order.</p>']
    for b in AVAILABILITY['lineups']:
        week9 = ', '.join(f'{slot} {name}' for slot, name in b['week9'])
        week10 = ', '.join(f'{slot} {name}' for slot, name in b['week10'])
        rows = [
            row([f'{b["abbr"]} {b["side"]} · Week 9 starters', week9, 'Official Game Book',
                 'Baseline lineup'], (GAMEBOOK[b['week9_source']],), 'Direct publisher / game book'),
            row([f'{b["abbr"]} {b["side"]} · Week 10 starters', week10, 'Official Game Book',
                 'Compared lineup'], (GAMEBOOK[b['week10_source']],), 'Direct publisher / game book'),
            row([f'{b["abbr"]} {b["side"]} · left the starting eleven', ', '.join(b['out']) or 'None',
                 'Computed set difference', 'Verified change'], (GAMEBOOK[b['week9_source']],GAMEBOOK[b['week10_source']]), 'Both game books'),
            row([f'{b["abbr"]} {b["side"]} · entered the starting eleven', ', '.join(b['in']) or 'None',
                 'Computed set difference', 'Verified change'], (GAMEBOOK[b['week9_source']],GAMEBOOK[b['week10_source']]), 'Both game books'),
        ]
        note = b.get('note')
        block = table(f'{b["team"]} — {b["side"]}', ['Scope','Players as published','Method','Reading'], rows)
        if note:
            block += f'<p class="note">{e(note)}</p>'
        out.append(block)
    return ''.join(out)


def _replacement_table():
    rows = []
    for item in AVAILABILITY['replacement_chain']:
        injury = item['injury_report_week10']
        rows.append(row([
            f'{item["player_out"]} ({item["position"]}, {item["team"]})',
            f'Week 10 report: {", ".join(injury["injuries"]) or "blank"} · {injury["practice_status"]} · game status {injury["game_status"] or "blank"}',
            'Yes — printed under Not Active' if item['independently_inactive'] else 'Not established',
            (f'{item["replacement_started"]} ({item["replacement_number"]})' if item['replacement_started'] else 'No starting slot changed'),
            item['depth_tier_of_replacement'],
            item['evidence'],
        ], ('nfl-gamebook-w10','nfl-injury'), 'Direct publisher / two documents'))
    return ('<h2>Replacement chains the official record supports</h2>'
            '<p>Three players were both ruled out on the official report and printed under Not Active in the same week. Only one of them occupied a starting slot in the previous game, so only one produced a verified replacement starter.</p>'
            + table('Verified replacement chains',['Player out','Official Week 10 designation','Independently inactive','Replacement that started','Replacement depth tier','Evidence trail'],rows)
            + '<p>The depth-tier column is populated with blanks on purpose. The NFL roster page publishes number, position, roster status, height, weight, age and college — and nothing that ranks a backup. No depth chart was obtainable from the league site. Filling this column would require inventing a field, so it stays empty and the limitation is published instead.</p>')

def _counterexamples():
    practice = AVAILABILITY['practice_status_counterexample']
    inactive = AVAILABILITY['no_designation_inactive_counterexample'][0]
    rows = [
        row([f'{p["player"]} ({p["position"]}, {p["team"]})',
             f'Injuries: {", ".join(p["injury_report_week10"]["injuries"]) or "blank"} · {p["injury_report_week10"]["practice_status"]} · game status {p["injury_report_week10"]["game_status"] or "blank"}',
             p['week10_outcome'], p['lesson']],
            ('nfl-injury', GAMEBOOK[p['source']]), 'Direct publisher / two documents')
        for p in practice
    ]
    rows.append(row([f'{inactive["team"]} inactive list',
        f'{inactive["inactives_without_any_week10_injury_designation"]} of {inactive["inactive_count"]} inactives had no Week 10 injury designation',
        ', '.join(inactive['inactive_list']), inactive['lesson']],
        (GAMEBOOK[inactive['source']], 'nfl-injury'), 'Direct publisher / two documents'))
    return ('<h2>Two official counterexamples</h2>'
            '<p>These are kept because they each kill a shortcut that would otherwise look reasonable. Both are re-checkable against the linked documents.</p>'
            + table('Where the naive reading fails',['Case','Official designation','What actually happened','Lesson for the model'],rows))


def _injury_table():
    rows = []
    for obs in INJURY['observations']:
        rows.append(row([f'{obs["player"]} · {obs["position"]} · {obs["abbr"]}',
                         ', '.join(obs['injuries']) or None,
                         obs['practice_status'],
                         obs['game_status'],
                         'Blank as published — not a clearance' if obs['game_status'] is None else 'Designation published'],
                        ('nfl-injury',), 'Direct publisher / weekly report'))
    return ('<h2>Official Week 10 injury report excerpt</h2>'
            f'<p>{e(INJURY["document_title"])}, two club tables only, retrieved {e(INJURY["retrieved_utc"])}. A blank game-status cell reproduces the published table and means no designation was shown — it does not mean the player was cleared.</p>'
            + table('Official injury observations',['Player / position / club','Injuries as published','Practice status','Game status','How to read the cell'],rows))


STATE_LABEL = {
    'decided': 'Decided',
    'decided_pending_data': 'Decided · waiting on data',
    'deferred': 'Deferred',
    'blocked': 'Blocked',
    'answered': 'Answered',
    'open_discoverable': 'Open · discoverable',
    'unknown_unpublished': 'Unknown · not published',
    'accepted': 'Accepted',
    'proposed': 'Proposed',
    'rejected': 'Rejected',
    'blocked_on_evidence': 'Blocked on evidence',
}


def _decision_rows():
    for d in BRIEF['decisions']:
        yield row([f'{d["id"]} · {d["decision"]}', d['default_if_nothing_changes'],
                   d['evidence_required'], d['current_blocker'] or 'None for the decision itself',
                   d['stopping_rule'], STATE_LABEL[d['state']], d['suggestion']])


page('decision.html','Decision brief','What to decide,\nand what would stop it.',
     'Every live decision this project supports, with the default if nothing changes and the stopping rule fixed before the evidence arrives. Nothing here is a recommendation to bet.',
     '<div class="notice"><strong>Default position: do nothing</strong><p>No decision below authorises a wager, a published line, or a reward. Where a decision is blocked, the honest action is to keep the field blank and work on the blocker.</p></div>'
     + table('Decision queue',['Decision','Default if nothing changes','Evidence required','Current blocker','Stopping rule (fixed in advance)','State','Suggestion'],list(_decision_rows()))
     + '<h2>Why a brief instead of a research summary</h2><p>A research summary records what was done. A brief records what is still open and what would end it. Without the second, an unknown can persist indefinitely because no row owns it. Every entry above names the artefact that would settle it, so the next action is visible without asking anyone.</p>'
     + _standing_constraints())

page('questions.html','Questions & answers','What must be known\nbefore deciding.',
     'A single register of the questions that have to be answered before a decision is reasonable, split into what is answered, what is still discoverable, and what the publisher does not release.',
     _counts_strip() + table('Question register',[
         'ID / group','Question','Information needed','Answer, if verified','Blocker / why not','State'],
         [row([f'{q["id"]} · {q["group"]}', q['question'], q['information_needed'],
               q.get('answer'), q.get('blocked_by') or 'Answered — see source', STATE_LABEL[q['state']]],
              tuple(q['sources']), 'Source for this row')
          for q in QUESTIONS['questions']])
     + '<p>A blank answer cell means the question is genuinely unanswered. It is not zero, not "no difference", and not a value to be filled in later from memory. Answers are limited to what the linked source actually states.</p>')

def _suggestion_rows():
    ordered = sorted(SUGGESTIONS['suggestions'], key=impact_rank)
    for i, s in enumerate(ordered, 1):
        yield row([f'{s["id"]} · #{i} · {s["category"]}', s['title'], s['problem'],
                   s['why_it_improves_decisions'], s['cost'], s['falsified_by'],
                   STATE_LABEL[s['status']]],
                  ('repo',), 'Project record')


def _suggestion_needs_rows():
    for s in SUGGESTIONS['suggestions']:
        if s.get('needs'):
            yield row([s['id'], s['title'], '; '.join(s['needs'])], ('repo',), 'Project record')


page('suggestions.html','Suggestions','Review before implementing.',
     'Every proposed improvement, scored on decision impact and evidence cost, with the statement that would falsify it. Select from this register rather than implementing by instinct.',
     '<div class="notice"><strong>How to use this page</strong><p>Read the "why it improves decisions" and "falsified by" columns first. A suggestion that cannot name what would falsify it should be rejected regardless of how appealing it sounds. Accepted items already have a matching decision on the Decision Brief.</p></div>'
     + _suggestion_summary()
     + table('Suggestion register',['ID / rank','Proposal','Problem it solves','Why it improves decisions','Cost','Falsified by','Status'], list(_suggestion_rows()))
     + table('What each suggestion still needs',['ID','Proposal','Missing artefact before it can proceed'], list(_suggestion_needs_rows()))
     + '<p>The ranking is predeclared: decision impact first, then evidence cost, then how hard the change is to undo. Scores are recorded by hand at 1–3 and are never derived from a result, so the order cannot be reverse-engineered to favour a finding.</p>')

page('availability.html','Availability tracker','Who actually started,\nnot who was listed.',
     'Official Game Book lineups compared across consecutive weeks, plus the official Week 10 injury report. Replacement depth tiers are blank because no depth chart could be obtained from the league site.',
     '<div class="notice"><strong>The request was second, third and fourth string</strong><p>The NFL publishes a game-day starting lineup and a roster status code. This project could not obtain a depth chart from the league site — the club depth-chart route returns an NFL 404 — and found no starter flag per snap or any first/second/third/fourth-string designation. This page therefore reports the verified part — who started, who left the lineup and who entered — and leaves every depth tier blank rather than guessing.</p></div>'
     + _lineup_tables() + _replacement_table() + _counterexamples() + _injury_table())

_preserved_source = (ROOT/'tools/pages_8de532d1.py').read_text()
_preserved_body = _preserved_source.split('"""', 2)[2]
exec(compile(_preserved_body, 'pages_8de532d1.py', 'exec'),
     {'page': page, 'table': table, 'row': row, 'e': e, 'PAGES': PAGES,
      '__name__': 'pages_8de532d1'})


page('injuries.html','Injuries & depth','Track who is actually out.','Injury and replacement tracking from official publications only. The Week 10 2026 snapshot below is transcribed from the league injury report retrieved on 14 Nov 2026; depth order comes from club-published depth charts retrieved the same day. Blank injury text means the report listed no injury description—never a verified healthy status.',
     '<div class="notice"><strong>What is verified today · what is not</strong><p>Verified: the league\'s Week 10 2026 report (160 players carry an explicit Out/Doubtful/Questionable game status across the 14 listed games), three club depth charts, and league news identifying who is expected to start. Not verified: historical point-in-time injury archives, participation snaps, certified game-day depth order (club charts are self-labeled "unofficial"), and any performance effect of a replacement. See <a href="flags.html">Flagged for Review</a> F19-F21.</p></div>'
     + table('Availability tracking contract',['Field tracked','Official source','Verified current state','Gap / rule'],[
         row(['Game status (Out/Doubtful/Questionable)','League injury report, per club per game','Captured for Week 10 2026 on 2026-11-14 ('+str(len(INJ))+' players).','No historical archive: statuses must be snapshotted each week with retrieval time; never infer a missing report as availability.'],('nfl-injury-w10',),'Direct publisher / snapshot'),
         row(['Practice status','League injury report (DNP / Limited / Full)','Captured for Week 10 2026 on 2026-11-14.','Practice participation is not a verified playing-time predictor; no direction asserted.'],('nfl-injury-w10',),'Direct publisher / snapshot'),
         row(['Depth order (1st/2nd/3rd/4th string)','Club depth charts (three clubs retrieved)','KC, SEA and DET charts captured 2026-11-14.','Charts are club-published and self-labeled "unofficial"; the other 29 clubs were not retrieved this session. No derived depth label may outlive its chart version.'],('chiefs-depth','seahawks-depth','lions-depth'),'Direct publisher / self-labeled unofficial'),
         row(['Expected starter changes','League news headlines linked from the report page','QB start changes for SEA, MIA, CLE, AZ and BAL IR placement verified as published links.','Headlines are league news, not box scores; actual lineups must be confirmed from the game before any evaluation.'],('nfl-injury-w10',),'Direct publisher / headline scope'),
         row(['Replacement performance delta','Not available from any retrieved source','Blank — no verified starter vs replacement performance sample exists.','Requires historical participation and production data with provenance; do not manufacture a drop-off number.'],('repo',),'Project gap / no source'),
         row(['Point-in-time capture','Project snapshot tables on this page','Snapshot tied to retrieval date 2026-11-14; statuses can change before kickoff.','A published report is not immutable; record retrieval UTC and refresh before lineup lock.'],('repo',),'Project record')
     ])
     + table('Verified Week 10 2026 game slate',['Listed first (record)','Listed second (record)','Kickoff · network (as listed)','Snapshot rows'],[
         row([f'{a} ({ar})',f'{b} ({br})',n, str(sum(1 for r in INJ if r[0] in (a,b)) or '')],('nfl-injury-w10',),'Direct publisher / transcribed') for a,ar,b,br,n,tv in SLATE
     ])
     + table('Week 10 2026 availability snapshot (players with an explicit Game Status)', ['Team','Player','Position','Injury (report text)','Practice status','Game status'], [
         row(list(r),('nfl-injury-w10',),'League injury report / verbatim') for r in INJ
     ])
     + table('Derived team availability burden', ['Team','Out','Doubtful','Questionable','Defense positions','Offense + OL positions','Special teams','Snapshot rows'], [
         row(list(t),('nfl-injury-w10',),'Derived arithmetic / not a performance metric') for t in burden_rows()
     ])
     + table('Verified depth-linked replacement examples',['Team · position (chart slot)','Unavailable or conditional','Next player up (published order)','Status of the replacement','News corroboration'],[
         row(['SEA · QB (1st)','Sam Darnold — Out (report)','Drew Lock — 2nd string (chart)','Limited practice, no game status on report','League news: "Drew Lock ... has no injury designation, will start for Seahawks vs. Raiders"'],('nfl-injury-w10','seahawks-depth'),'Two official sources + league news'),
         row(['SEA · LT (1st)','Charles Cross — Out (report)','Josh Jones — 2nd string (chart)','Not listed on the report','None retrieved'],('nfl-injury-w10','seahawks-depth'),'Two official sources'),
         row(['SEA · LG (1st)','Quenton Nelson — Out (report)','Anthony Bradford — 2nd string LG (chart)','Not listed on the report; also 2nd RG on the chart','None retrieved'],('nfl-injury-w10','seahawks-depth'),'Two official sources'),
         row(['SEA · DT slot 1 (1st)','Leonard Williams — Out (report)','Rylie Mills — 2nd string (chart)','Not listed on the report','None retrieved'],('nfl-injury-w10','seahawks-depth'),'Two official sources'),
         row(['KC · RT (1st)','Jaylon Moore — Out (report)','Joshua Ezeudu — 2nd string RT (chart)','Not listed on the report; also 2nd LG','None retrieved'],('nfl-injury-w10','chiefs-depth'),'Two official sources'),
         row(['KC · RB (1st)','Kenneth Walker III — Questionable (report)','Emmett Johnson — 2nd string (chart); Jaydn Ott 3rd is himself Questionable','Conditional: order applies only if the starter cannot play','None retrieved'],('nfl-injury-w10','chiefs-depth'),'Two official sources / conditional'),
         row(['DET · C (1st)','Cade Mays — Out (report)','Juice Scruggs — 2nd string (chart)','Not listed on the report','None retrieved'],('nfl-injury-w10','lions-depth'),'Two official sources'),
         row(['DET · CB slot 1 (1st)','D.J. Reed — Out (report)','Rock Ya-Sin — 2nd string (chart)','Not listed on the report','None retrieved'],('nfl-injury-w10','lions-depth'),'Two official sources'),
         row(['DET · S','Kerby Joseph — Out (report), but absent from the club chart\'s safety rows','Unverified — the two official sources conflict; no replacement may be inferred','—','See Flagged for Review F14'],('nfl-injury-w10','lions-depth','repo'),'Cross-source conflict / withheld'),
         row(['MIA · QB (1st)','Malik Willis — placed on injured reserve (league news)','Kyle McCord — "in line for first start" (league news)','Depth slot not published on any retrieved chart','League news: "Dolphins place QB Malik Willis (groin) on injured reserve; Kyle McCord in line for first start"'],('nfl-injury-w10',),'League news only / depth unverified'),
         row(['BAL · QB (1st)','Lamar Jackson — officially placed on injured reserve (league news)','Blank — no verified depth chart or start announcement retrieved this session','—','League news: "Ravens officially place Lamar Jackson on injured reserve"; earlier: right thumb, out 6-9 weeks'],('nfl-injury-w10',),'League news only / replacement unverified'),
         row(['GB · RB (1st)','Josh Jacobs — Out (report); league news reports finger surgery, return timeline TBD','Blank — no GB depth chart retrieved this session; no replacement inferred','—','League news: "Packers RB Josh Jacobs to undergo surgery on finger this week"'],('nfl-injury-w10',),'Injury verified / replacement unverified'),
     ])
     + table('Deficiency signal methodology (proposed; unvalidated)',['Signal','Definition (frozen before use)','Data required','Current state'],[
         row(['Depth drop index','Strings travelled by the next player up: 1st→2nd = 1, 1st→3rd = 2; unit sums over all Out/Doubtful slots.','Certified per-game depth order plus game-status snapshot, both point-in-time.','Design only; certified depth unavailable (club charts self-labeled unofficial).'],('chiefs-depth','lions-depth','repo'),'Proposal / partially sourced'),
         row(['Unit availability burden','Count of Out/Doubtful/Questionable in a position unit, as published in the table above.','Weekly report snapshot (verified for Week 10 2026).','Counts published for Week 10; no performance weighting — any effect size is unknown.'],('nfl-injury-w10',),'Derived counts / effect unknown'),
         row(['Replacement performance delta','Starter\'s baseline vs replacement\'s production in comparable situations, same season.','Historical participation and production with provenance and stable player IDs.','Blank — no verified historical sample; do not invent a drop-off number.'],('nfl-stats','repo'),'No source / blank'),
         row(['Defense deficiency score','Weighted unit burden on the defensive side (DL/LB/DB) entering a game.','Verified depth order, weight study, and a power-defined sample before use.','Not implemented; weights unset by design until data exists.'],('nfl-injury-w10','multiplicity','repo'),'Proposal / not implemented'),
         row(['Offense deficiency score','Same construction for offensive units, separate weights and gates.','Same as above; offense and defense never share a weight set.','Not implemented.'],('nfl-injury-w10','repo'),'Proposal / not implemented')
     ])
     + '<p>Snapshot integrity: the tables above are a single point-in-time transcription (retrieved 2026-11-14) of the official report; statuses can change before kickoff and the report page does not publish a revision timestamp. Cross-source conflicts are published on <a href="flags.html">Flagged for Review</a>, never silently reconciled. Strategy use of these inputs remains subject to the <a href="validation.html">validation gates</a>; no injury-adjusted edge is asserted. See <a href="questions.html">Decision questions</a> for what must be solved before any depth-weighted signal is trusted.</p>')


_own9_source = (ROOT/'tools/pages_4f2e0291.py').read_text()
_own9_body = _own9_source.split('"""', 2)[2]
exec(compile(_own9_body, 'pages_4f2e0291.py', 'exec'),
     {'page': page, 'table': table, 'row': row, 'e': e, 'PAGES': PAGES, 'ROOT': ROOT,
      '__name__': 'pages_4f2e0291'})


def render():
    files = {}
    for filename,(label,title,intro,content) in PAGES.items():
        nav = ''.join(
            f'<span class="nav-group"><span class="nav-label">{e(group)}</span>'
            + ''.join(f'<a href="{f}"'+(' aria-current="page"' if f==filename else '')+f'>{e(label)}</a>' for f,label in items)
            + '</span>' for group,items in NAV_GROUPS)
        page_date = '14 Nov 2026' if filename in KEEP_DATE_14 else '04 Nov 2026'
        files[filename] = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-first NFL research dashboard. Strategies, validation, correlation requirements and transparent limitations."><title>{e(label)} · Own9 NFL Research</title><link rel="stylesheet" href="style.css"><script src="site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="shell top"><a class="brand" href="index.html"><span>O9</span> OWN9 <small> / NFL RESEARCH</small></a><span class="status-dot">Research only · no live wagers</span></div><nav class="shell" aria-label="Main navigation">{nav}</nav></header>
<main class="shell" id="main"><div class="page-meta"><span class="eyebrow">RESEARCH DESK / {e(label.upper())}</span><span>As of {e(page_date)} · UTC</span></div><h1>{e(title).replace(chr(10),'<br>')}</h1><p class="lead">{e(intro)}</p><div class="filter" hidden><label for="row-search">Find a table entry</label><input id="row-search" type="search" placeholder="Filter this page…" autocomplete="off"><span id="row-count" role="status" aria-live="polite"></span></div>{content}<p class="disclaimer">Research, not betting advice. No verified edge or guaranteed return. Blank empirical values are unavailable and unverified, never zero.</p></main>
<footer class="shell"><b>OWN9 / NFL RESEARCH</b><span>Evidence over assumptions · <a href="sources.html">Evidence register</a> · <a href="flags.html">Flagged for Review</a></span></footer></body></html>\n'''
    return files

if __name__ == '__main__':
    for filename,content in render().items():
        (ROOT/filename).write_text(content)
    print(f'Rendered {len(PAGES)} static pages.')
