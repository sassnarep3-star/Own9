"""Deterministic static renderer; no network calls, no invented NFL metrics."""
import json
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {s['id']: s for s in json.loads((ROOT/'evidence/sources.json').read_text())}
PAGES = {}

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

page('injuries.html','Injuries & depth','Track who is actually out.','Injury and replacement tracking from official publications only. The Week 10 2026 snapshot below is transcribed from the league injury report retrieved on 14 Nov 2026; depth order comes from club-published depth charts retrieved the same day. Blank injury text means the report listed no injury description—never a verified healthy status.',
     '<div class="notice"><strong>What is verified today · what is not</strong><p>Verified: the league\'s Week 10 2026 report (160 players carry an explicit Out/Doubtful/Questionable game status across the 14 listed games), three club depth charts, and league news identifying who is expected to start. Not verified: historical point-in-time injury archives, participation snaps, certified game-day depth order (club charts are self-labeled "unofficial"), and any performance effect of a replacement. See <a href="flags.html">Flagged for Review</a> F13-F15.</p></div>'
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

page('sources.html','Sources','The evidence register.',
     'Official publisher pages read on 04 Nov 2026 and re-read in full scope on 14 Nov 2026 (all 14 manifest entries), with the precise claim supported and limits. A retrieved page is not a verified NFL model. Source contents can change.',
     table('Official source review',['Reference ID','Supported scope','Limits / evidence state','Checked UTC date'],[
         row([s['id'],s['supports'],s['scope']+' ['+s['status']+']',s['checked']],(s['id'],),'Direct publisher / checked scope') for s in SOURCES.values()
     ]) + '<p>Each row throughout the dashboard links to a publisher reference or this project’s primary repository record. Labels distinguish direct support, contextual background, mathematical specification and project proposals. The <a href="evidence/sources.json">machine-readable manifest</a> records the same scope. References do not endorse betting strategies.</p>')

page('audit.html','Repository audit','Review the implementation, too.',
     'The session began at commit 71236ddd74208838537d87ecfe722e578671f69f. All 11 tracked files at that checkout were read; PR #2 corrections and subsequent coordination records were preserved before integration.',
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
         row(['Site generator / checker / CI','Deterministic generation, local asset/fragment checks, all table rows have known sources, blank empirical metrics and Python test suite.','Remote reachability is not established by local checks; no automated claim-entailment certification.'])
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
         row(['F13 · Review','Club depth charts are self-labeled "unofficial" even on official club sites (KC, SEA, DET retrieved 2026-11-14); no league-certified game-day depth order was found in any retrieved source.','Depth-slot attributions on the injury page carry both the chart link and this caveat; verify against actual game participation before any starter-replaced claim is used in a signal. The other 29 clubs were not retrieved this session.','Published limitation'],('chiefs-depth','seahawks-depth','lions-depth','repo'),'Direct publisher observation / scope'),
         row(['F14 · Review','Cross-source conflict: DET S Kerby Joseph carries an Out game status on the Week 10 2026 league report but is absent from the club depth chart\'s safety rows (both retrieved 2026-11-14).','Conflicting official publications must be surfaced, not reconciled; no replacement is inferred for that slot. Similar conflicts may exist for clubs whose charts were not retrieved.','Unresolved — manual review'],('nfl-injury-w10','lions-depth','repo'),'Cross-source conflict / withheld'),
         row(['F15 · Review','The Week 10 2026 injury snapshot is a single point-in-time retrieval: the report page publishes no revision timestamp, roster assignments were not cross-verified against a second independent official source, and no historical point-in-time injury/depth archive exists in verified evidence.','Snapshot rows are tied to retrieval UTC 2026-11-14 and must be refreshed before lineup lock; F02/F08 gaps stand. Injury data confers no validated predictive edge.','Snapshot dated / archive missing'],('nfl-injury-w10','repo'),'Snapshot limitation / project gap')
     ]) + '<p>Independent earlier-baseline technical report: <a href="release-checks/index.html">release quality review</a>. Its stored five-page / 28-row snapshot predates this nine-page integration; it is not a current factual or deployment certification.</p><p>Separate inherited, uncertified analysis: <a href="https://github.com/sassnarep3-star/Own9/pull/6">PR #6 and its stated evidence limitations</a>; <a href="research/flagged.html">its separate review register</a>. Its numerical findings are not adopted by this dashboard.</p>'
     + '<p>Review registers and reports in linked subsites (each governed by its owning session\'s scope): <a href="site/review.html">site/ review (F01-F13)</a> · <a href="strict-lab/flags.html">strict-lab/ flags (F01-F12)</a> · <a href="research/flagged.html">research/ flagged (F1-F8)</a> · <a href="own9-research/flags.html">own9-research/ flags</a> · <a href="release-checks/index.html">release-checks/ report</a> · <a href="release-checks/expanded-review.html">expanded source-policy review</a> · <a href="independent-audit/flags.html">independent-audit/ flags</a>. Subsite findings are published by their owning sessions; this root dashboard neither certifies nor adopts them.</p>')


def render():
    files = {}
    for filename,(label,title,intro,content) in PAGES.items():
        nav = ''.join(f'<a href="{f}"'+(' aria-current="page"' if f==filename else '')+f'>{e(v[0])}</a>' for f,v in PAGES.items())
        files[filename] = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-first NFL research dashboard. Strategies, validation, correlation requirements and transparent limitations."><title>{e(label)} · Own9 NFL Research</title><link rel="stylesheet" href="style.css"><script src="site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="shell top"><a class="brand" href="index.html"><span>O9</span> OWN9 <small> / NFL RESEARCH</small></a><span class="status-dot">Research only · no live wagers</span></div><nav class="shell" aria-label="Main navigation">{nav}</nav></header>
<main class="shell" id="main"><div class="page-meta"><span class="eyebrow">RESEARCH DESK / {e(label.upper())}</span><span>As of 14 Nov 2026 · UTC</span></div><h1>{e(title).replace(chr(10),'<br>')}</h1><p class="lead">{e(intro)}</p><div class="filter" hidden><label for="row-search">Find a table entry</label><input id="row-search" type="search" placeholder="Filter this page…" autocomplete="off"><span id="row-count" role="status" aria-live="polite"></span></div>{content}<p class="disclaimer">Research, not betting advice. No verified edge or guaranteed return. Blank empirical values are unavailable and unverified, never zero.</p></main>
<footer class="shell"><b>OWN9 / NFL RESEARCH</b><span>Evidence over assumptions · <a href="sources.html">Evidence register</a> · <a href="flags.html">Flagged for Review</a></span></footer></body></html>\n'''
    return files

if __name__ == '__main__':
    for filename,content in render().items():
        (ROOT/filename).write_text(content)
    print(f'Rendered {len(PAGES)} static pages.')
