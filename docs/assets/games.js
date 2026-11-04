// Games table: client-side filtering and paging over data/games.json.
// Scores and lines are hidden unless the user opts in, because they are unverified (see flagged.html).
(function () {
  var PAGE = 50, rows = [], filtered = [], page = 0;
  var el = function (id) { return document.getElementById(id); };
  var fmt = function (v, d) { return v === null || v === undefined ? "—" : Number(v).toFixed(d === undefined ? 1 : d); };
  var esc = function (s) { return String(s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); };
  var verifiedIds = { "2025_01_KC_LAC": 1, "2025_09_BAL_MIA": 1 };
  var wk9 = { "2026_09_LV_SF": "Kickoff mismatch vs nfl.com (flagged F3)" };

  function status(g) {
    if (verifiedIds[g.game_id]) return '<span class="tag ver">Verified (score on nfl.com)</span>';
    if (wk9[g.game_id]) return '<span class="tag unv">' + wk9[g.game_id] + '</span>';
    if (g.status === "scheduled") return g.season === 2026 && g.week === 9
      ? '<span class="tag ver">Scheduled: nfl.com ✔</span>' : '<span class="tag unv">Scheduled · Unverified</span>';
    return '<span class="tag unv">Unverified</span>';
  }

  function render() {
    var show = el("f-show").checked;
    var start = page * PAGE, slice = filtered.slice(start, start + PAGE);
    var tb = document.querySelector("#games-table tbody");
    tb.innerHTML = slice.map(function (g) {
      var score = (g.away_score === null) ? "—" : g.away_score + " – " + g.home_score;
      var sp = show ? fmt(g.spread_home) : "—";
      var tot = show ? fmt(g.total_line) : "—";
      var ml = show ? (g.home_ml === null ? "—" : g.home_ml) : "—";
      var ol = show ? fmt(g.model_line_home, 2) : "—";
      var sc = show ? score : (verifiedIds[g.game_id] ? score : "—");
      var srcs = '<a href="' + g.nflverse_row + '" target="_blank" rel="noopener">nflverse ↗</a>' +
        (g.nfl_com ? ' · <a href="' + g.nfl_com + '" target="_blank" rel="noopener">nfl.com ↗</a>' : "");
      return "<tr><td>" + g.season + "</td><td>" + g.game_type + "</td><td>" + g.week + "</td><td>" + g.date +
        "</td><td>" + esc(g.away) + "</td><td>" + esc(g.home) + "</td><td>" + sc + "</td><td>" + sp +
        "</td><td>" + tot + "</td><td>" + ml + "</td><td>" + ol + "</td><td>" + status(g) + "</td><td>" + srcs + "</td></tr>";
    }).join("");
    var pages = Math.max(1, Math.ceil(filtered.length / PAGE));
    el("pg").textContent = "Page " + (page + 1) + " of " + pages;
    el("count").textContent = filtered.length.toLocaleString() + " games";
    el("prev").disabled = page === 0;
    el("next").disabled = page >= pages - 1;
  }

  function apply() {
    var s = el("f-season").value, t = el("f-team").value.trim().toUpperCase(), st = el("f-status").value;
    filtered = rows.filter(function (g) {
      if (s && String(g.season) !== s) return false;
      if (t && g.away !== t && g.home !== t) return false;
      if (st === "verified" && !verifiedIds[g.game_id]) return false;
      if (st === "scheduled" && g.status !== "scheduled") return false;
      if (st === "unverified" && (verifiedIds[g.game_id] || g.status === "scheduled")) return false;
      return true;
    });
    page = 0; render();
  }

  fetch("data/games.json").then(function (r) { return r.json(); }).then(function (data) {
    rows = data.slice().reverse(); // newest first
    var seasons = Array.from(new Set(data.map(function (g) { return g.season; }))).sort(function (a, b) { return b - a; });
    seasons.forEach(function (y) { var o = document.createElement("option"); o.value = y; o.textContent = y; el("f-season").appendChild(o); });
    ["f-season", "f-team", "f-status", "f-show"].forEach(function (id) { el(id).addEventListener("input", apply); el(id).addEventListener("change", apply); });
    el("prev").onclick = function () { if (page > 0) { page--; render(); } };
    el("next").onclick = function () { page++; render(); };
    apply();
  }).catch(function () { el("count").textContent = "Could not load data/games.json"; });
})();
