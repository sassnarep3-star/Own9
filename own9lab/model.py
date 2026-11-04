"""Point-in-time line origination model.

points(team i vs j) = mu + v*eta/2 + off_i - def_j + e,  v = +1 home, -1 away, 0 neutral site
fit by weighted ridge on officially VERIFIED results only; weights decay with age (tau days)
and are multiplied by kappa for every season boundary crossed (off-season regression).
Ratings for a (season, week) use only games played strictly before that week's first game.

Originated lines per game:
  spread_hat = home margin (positive = home favoured, same sign as nflverse spread_line)
  total_hat  = expected combined points
  p_home     = Phi(spread_hat / sigma)   (sigma fitted on development seasons only)
  fair moneylines from p_home (no vig)
Hyper-parameters are chosen on DEV_SEASONS only (MSE); test/forward seasons are never used.
"""
import itertools, json
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import norm
from . import config as C

FRANCHISE = {"SD": "LAC", "STL": "LA", "OAK": "LV"}
GRID = {"tau": [90, 180, 365, 730], "kappa": [0.4, 0.6, 0.8], "lam": [2.0, 5.0, 15.0]}
WINDOW_DAYS = 4 * 365  # older games have negligible weight under every grid value


def load_games():
    g = pd.read_csv(C.DERIVED / "games.csv", dtype={"old_game_id": str})
    g["date"] = pd.to_datetime(g.gameday)
    g["home_f"] = g.home_team.replace(FRANCHISE)
    g["away_f"] = g.away_team.replace(FRANCHISE)
    g["neutral"] = (g.location == "Neutral").astype(int)
    return g.sort_values(["date", "game_id"]).reset_index(drop=True)


class Fitter:
    def __init__(self, g):
        self.g = g
        self.teams = sorted(set(g.home_f) | set(g.away_f))
        self.ix = {t: i for i, t in enumerate(self.teams)}
        tr = g[g.score_status == "VERIFIED"].copy()
        self.tr = tr
        n, T = len(tr), len(self.teams)
        P = 2 + 2 * T
        X = np.zeros((2 * n, P))
        hi = tr.home_f.map(self.ix).to_numpy()
        ai = tr.away_f.map(self.ix).to_numpy()
        v = 1 - tr.neutral.to_numpy()
        r = np.arange(n)
        X[:n, 0] = 1; X[:n, 1] = v / 2; X[r, 2 + hi] = 1; X[r, 2 + T + ai] = -1
        X[n:, 0] = 1; X[n:, 1] = -v / 2; X[n + r, 2 + ai] = 1; X[n + r, 2 + T + hi] = -1
        self.X = X
        self.y = np.concatenate([tr.home_score.to_numpy(float), tr.away_score.to_numpy(float)])
        self.days = np.concatenate([tr.date.to_numpy()] * 2)
        self.season = np.concatenate([tr.season.to_numpy()] * 2)
        self.T, self.P = T, P

    def fit(self, cutoff, season, tau, kappa, lam):
        """Ratings using only verified games with date < cutoff."""
        age = (np.datetime64(cutoff) - self.days) / np.timedelta64(1, "D")
        m = (age > 0) & (age <= WINDOW_DAYS)
        if m.sum() < 64:
            return None, 0, None
        w = np.exp(-age[m] / tau) * kappa ** (season - self.season[m])
        X, y = self.X[m], self.y[m]
        A = (X * w[:, None]).T @ X
        A[2:, 2:] += lam * np.eye(self.P - 2)
        b = (X * w[:, None]).T @ y
        last = str(pd.Timestamp(self.days[m].max()).date())
        return np.linalg.solve(A, b), int(m.sum() // 2), last

    def predict(self, beta, home, away, neutral):
        T = self.T
        h, a = self.ix[home], self.ix[away]
        v = 0 if neutral else 1
        mu, eta = beta[0], beta[1]
        hp = mu + v * eta / 2 + beta[2 + h] - beta[2 + T + a]
        ap = mu - v * eta / 2 + beta[2 + a] - beta[2 + T + h]
        return hp - ap, hp + ap


def weekly_predictions(g, fitter, tau, kappa, lam, seasons=None):
    rows = []
    sel = g if seasons is None else g[g.season.isin(seasons)]
    for (season, week), grp in sel.groupby(["season", "week"], sort=True):
        cutoff = grp.date.min()
        beta, n_used, last = fitter.fit(cutoff, season, tau, kappa, lam)
        if beta is None:
            continue
        for r in grp.itertuples():
            s, t = fitter.predict(beta, r.home_f, r.away_f, r.neutral)
            rows.append((r.game_id, s, t, last, n_used))
    return pd.DataFrame(rows, columns=["game_id", "spread_hat", "total_hat", "data_through", "n_games_used"])


def tune(g, fitter):
    dev = g[g.season.isin(C.DEV_SEASONS) & (g.score_status == "VERIFIED")]
    res = []
    for tau, kappa, lam in itertools.product(GRID["tau"], GRID["kappa"], GRID["lam"]):
        p = weekly_predictions(g, fitter, tau, kappa, lam, seasons=C.DEV_SEASONS).merge(dev, on="game_id")
        margin = p.home_score - p.away_score
        res.append({"tau": tau, "kappa": kappa, "lam": lam,
                    "mse_margin": float(((margin - p.spread_hat) ** 2).mean()),
                    "mse_total": float(((p.home_score + p.away_score - p.total_hat) ** 2).mean()), "n": len(p)})
    return pd.DataFrame(res)


def fit_sigma(pred):
    d = pred[(pred.home_score != pred.away_score)]
    yhome = (d.home_score > d.away_score).to_numpy()
    s = d.spread_hat.to_numpy()

    def nll(sig):
        p = np.clip(norm.cdf(s / sig), 1e-9, 1 - 1e-9)
        return -np.mean(np.where(yhome, np.log(p), np.log(1 - p)))
    return float(minimize_scalar(nll, bounds=(5, 30), method="bounded").x)


def american(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.where(p >= 0.5, -100 * p / (1 - p), 100 * (1 - p) / p)


def run():
    g = load_games()
    fitter = Fitter(g)
    grid = tune(g, fitter)
    bm = grid.loc[grid.mse_margin.idxmin()]
    bt = grid.loc[grid.mse_total.idxmin()]
    pm = weekly_predictions(g, fitter, bm.tau, bm.kappa, bm.lam)
    pt = weekly_predictions(g, fitter, bt.tau, bt.kappa, bt.lam)[["game_id", "total_hat"]]
    pred = pm.drop(columns="total_hat").merge(pt, on="game_id")
    dev = pred.merge(g[g.season.isin(C.DEV_SEASONS) & (g.score_status == "VERIFIED")], on="game_id")
    sigma = fit_sigma(dev)
    pred["p_home"] = norm.cdf(pred.spread_hat / sigma)
    pred["fair_ml_home"] = american(pred.p_home).round(0)
    pred["fair_ml_away"] = american(1 - pred.p_home).round(0)
    pred.to_csv(C.DERIVED / "model_predictions.csv", index=False, float_format="%.4f")
    params = {"margin": {k: float(bm[k]) for k in ("tau", "kappa", "lam")},
              "total": {k: float(bt[k]) for k in ("tau", "kappa", "lam")},
              "sigma": sigma, "tuned_on": f"{min(C.DEV_SEASONS)}-{max(C.DEV_SEASONS)}",
              "grid": GRID, "window_days": WINDOW_DAYS}
    grid.to_csv(C.DERIVED / "model_tuning_grid.csv", index=False, float_format="%.4f")
    (C.DERIVED / "model_params.json").write_text(json.dumps(params, indent=2) + "\n")
    return pred, params


if __name__ == "__main__":
    pred, params = run()
    print(json.dumps(params, indent=2))
    print(pred.tail(5))
