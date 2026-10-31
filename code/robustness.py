"""AP4 robustness analyses on the adopted baseline (corrected data, Equip + Raw merged, 3 assets).

Approved by the author on 2026-10-31. Reuses the v2 logic in pipeline.py unchanged; everything here is
added analysis. No figures (matplotlib not installed; AP5).

Reads (never writes): data/data_corrected.xlsx, data/raw/4CPBFP.xlsx
Writes: outputs/<tag>_results.json, <tag>_report.txt (default tag ap4_d6;
        the first AP4 run, before D6, is tag ap4 with --v2-first-row)

Usage (from this folder):  python -P robustness.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -P drops the script folder
import pipeline as P  # noqa: E402

DATA_CORR = P.ROOT / "data" / "data_corrected.xlsx"
ASSETS = ["Immobilière", "Automobile", "Equipement"]
P.ASSETS = ASSETS  # merged baseline (D3)
RF_BASE = 0.045
LO_BASE = np.array([0.02, 0.02, 0.02])
HI_BASE = np.array([0.70, 1.00, 1.00])
OOS_START = 36          # months of real returns before the first out-of-sample month
ROLL_WINDOW = 36
N_BOOT = 1000
BLOCK = 6
COSTS_BP = [0, 10, 25, 50]
DROP_FIRST = True  # decision D6 (2026-10-31); --v2-first-row restores the v2 convention


def est_rows(r):
    """Rows used for mu/cov: the 77 real returns (D6), or v2's 78 rows with the filled first zero."""
    return r.iloc[1:] if DROP_FIRST else r


# --- data -------------------------------------------------------------------
def load_murabaha(gap_variant="main"):
    m = P.load_murabaha_data(DATA_CORR)
    if gap_variant != "main":
        if gap_variant == "log_linear_interpolation":
            alt = pd.read_excel(DATA_CORR, sheet_name="gap_alternatives")
            alt = alt[alt["method"] == gap_variant]
            for _, row in alt.iterrows():
                d = pd.to_datetime(row["Date"], format="%Y-%m")
                for c in alt.columns[2:]:
                    m.loc[d, c] = row[c]
        else:  # "low" / "high" ends of the rounding interval of BAM's published variation
            b = pd.read_excel(DATA_CORR, sheet_name="estimate_bounds")
            for _, row in b.iterrows():
                m.loc[pd.to_datetime(row["Date"], format="%Y-%m"), row["column"]] = row[gap_variant]
    m["Equipement"] = m["Equipement"] + m["Matieres Premieres"]
    return m


BS = P.load_and_transpose_balance_sheet(P.BFP_PATH)


def build(gap_variant="main", clip=P.RETURN_CAP):
    merged = P.merge_datasets(load_murabaha(gap_variant), BS)
    r, unclipped = P.compute_returns(merged, return_cap=clip if clip is not None else 1e9)
    return merged, r[ASSETS], unclipped[ASSETS]


# --- optimisers (same objective as v2, bounds as arguments) -----------------
def max_sharpe(mu, cov, rf, lo=LO_BASE, hi=HI_BASE, n_starts=6, seed=0):
    mu, cov = np.asarray(mu, float), np.asarray(cov, float)
    n = len(mu)
    rng = np.random.default_rng(seed)
    starts = [np.full(n, 1.0 / n)] + [rng.dirichlet(np.ones(n)) for _ in range(n_starts - 1)]
    best = None
    for x0 in starts:
        res = minimize(P.negative_sharpe_ratio, x0, args=(mu, cov, rf), method="SLSQP",
                       bounds=list(zip(lo, hi)), constraints=({"type": "eq", "fun": lambda w: w.sum() - 1},),
                       options={"maxiter": 1000, "ftol": 1e-12})
        if res.success and (best is None or res.fun < best.fun):
            best = res
    if best is None:
        raise RuntimeError("max_sharpe: no start converged")
    return best.x


def min_var(cov, lo=LO_BASE, hi=HI_BASE, mu=None, target=None):
    cov = np.asarray(cov, float)
    n = cov.shape[0]
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    if target is not None:
        cons.append({"type": "eq", "fun": lambda w: w @ mu - target})
    res = minimize(lambda w: w @ cov @ w, np.full(n, 1.0 / n), jac=lambda w: 2 * cov @ w, method="SLSQP",
                   bounds=list(zip(lo, hi)), constraints=cons, options={"maxiter": 1000, "ftol": 1e-15})
    return res.x, bool(res.success)


def risk_parity(cov, lo=LO_BASE, hi=HI_BASE):
    """Equal risk contribution. Unconstrained ERC via Spinu's convex form, then a bounded version."""
    cov = np.asarray(cov, float)
    n = cov.shape[0]
    res = minimize(lambda x: 0.5 * x @ cov @ x - np.log(x).sum() / n, np.full(n, 1.0),
                   bounds=[(1e-9, None)] * n, method="L-BFGS-B")
    erc = res.x / res.x.sum()

    def spread(w):
        rc = w * (cov @ w)
        rc = rc / rc.sum()
        return ((rc - 1.0 / n) ** 2).sum()
    resb = minimize(spread, np.clip(erc, lo, hi) / np.clip(erc, lo, hi).sum(), method="SLSQP",
                    bounds=list(zip(lo, hi)), constraints=({"type": "eq", "fun": lambda w: w.sum() - 1},),
                    options={"maxiter": 1000, "ftol": 1e-15})
    return erc, resb.x


def perf(w, mu, cov, rf=RF_BASE):
    ret, vol = P.portfolio_performance(np.asarray(w), np.asarray(mu), np.asarray(cov))
    return {"weights": dict(zip(ASSETS, map(float, w))), "return": ret, "volatility": vol,
            "sharpe": (ret - rf) / vol}


def annual(r):
    return r.mean().values * 12, r.cov().values * 12


def lw_cov(r):
    return LedoitWolf().fit(r.values).covariance_ * 12


def bayes_stein_mu(r):
    """Jorion (1986) Bayes-Stein shrinkage of the mean toward the minimum-variance portfolio mean (monthly)."""
    x = r.values
    T, n = x.shape
    mu = x.mean(0)
    S = np.cov(x, rowvar=False)
    Si = np.linalg.inv(S)
    one = np.ones(n)
    mu0 = (one @ Si @ mu) / (one @ Si @ one)
    d = mu - mu0
    phi = (n + 2) / ((n + 2) + T * d @ Si @ d)
    return (1 - phi) * mu * 12 + phi * mu0 * 12, float(phi)


def describe(w):
    return {a: round(float(x), 4) for a, x in zip(ASSETS, w)}


def binding(w, lo, hi, tol=1e-6):
    return [f"{a}{'@floor' if abs(x - l) < tol else '@cap'}" for a, x, l, h in zip(ASSETS, w, lo, hi)
            if abs(x - l) < tol or abs(x - h) < tol]


# --- analyses ----------------------------------------------------------------
def main():
    import argparse
    global DROP_FIRST
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-first-row", action="store_true", help="keep v2's filled first-row zero in mu/cov")
    ap.add_argument("--tag", default="ap4_d6")
    args = ap.parse_args()
    DROP_FIRST = not args.v2_first_row
    sys.stdout.reconfigure(encoding="utf-8")
    out = {"settings": {"data": DATA_CORR.relative_to(P.ROOT).as_posix(), "assets": ASSETS, "rf_base": RF_BASE,
                        "bounds_base": {"lower": LO_BASE.tolist(), "upper": HI_BASE.tolist()},
                        "oos_start_months": OOS_START, "rolling_window": ROLL_WINDOW,
                        "n_boot": N_BOOT, "block_length": BLOCK, "seed": P.RNG_SEED,
                        "drop_first_row_zero": DROP_FIRST}}

    merged, R, U = build()
    mu, cov = annual(est_rows(R))
    rf_est, rf_info = P.estimate_shariah_reference_rate(merged)
    base_w = max_sharpe(mu, cov, RF_BASE)
    out["baseline"] = perf(base_w, mu, cov) | {"binding": binding(base_w, LO_BASE, HI_BASE),
                                              "rf_estimate_clipped": rf_est, "rf_info": rf_info}
    Rr, Ur = R.iloc[1:], U.iloc[1:]  # real returns only (77)

    # 1. Rf grid
    rf_grid = {"0%": 0.0, "2% (v2 floor)": 0.02, "3%": 0.03, "4.5% (v2 ceiling, baseline)": 0.045,
               "PSIA 24m median, unclipped": rf_info["rf_raw_unclipped"],
               "PSIA 24m mean, unclipped": rf_info["rf_raw_mean_instead_of_median"]}
    out["rf_grid"] = {k: perf(max_sharpe(mu, cov, v), mu, cov, v) | {"rf": v} for k, v in rf_grid.items()}

    # 2. Cap / floor grid
    grid = []
    for cap in [0.50, 0.60, 0.70, 0.80, 1.00]:
        for floor in [0.00, 0.01, 0.02, 0.05]:
            lo, hi = np.full(3, floor), np.array([cap, 1.0, 1.0])
            w = max_sharpe(mu, cov, RF_BASE, lo, hi)
            grid.append({"re_cap": cap, "floor": floor} | perf(w, mu, cov) | {"binding": binding(w, lo, hi)})
    out["cap_floor_grid"] = grid

    # 3. Winsorisation grid
    clip_rows = {}
    for clip in [0.05, 0.10, 0.15, 0.20, None]:
        _, Rc, Uc = build(clip=clip)
        m, c = annual(est_rows(Rc))
        w = max_sharpe(m, c, RF_BASE)
        clip_rows[f"±{int(clip*100)}%" if clip else "none"] = perf(w, m, c) | {
            "mu": dict(zip(ASSETS, map(float, m))), "binding": binding(w, LO_BASE, HI_BASE),
            "n_clipped": {a: int((Uc[a].iloc[1:].abs() > clip).sum()) if clip else 0 for a in ASSETS}}
    out["clip_grid"] = clip_rows

    # 4. Gap-month treatment (Nov 2019, May 2020)
    gaps = {}
    for g in ["main", "low", "high", "log_linear_interpolation"]:
        _, Rg, _ = build(gap_variant=g)
        m, c = annual(est_rows(Rg))
        gaps[g] = perf(max_sharpe(m, c, RF_BASE), m, c)
    out["gap_variants"] = gaps

    # 5. Estimation choices: first-row zero, simple returns, shrinkage
    est = {}
    m, c = annual(R if DROP_FIRST else Rr)
    label = "v2 first-row zero kept (78 rows)" if DROP_FIRST else "drop v2 first-row zero (77 obs)"
    est[label] = perf(max_sharpe(m, c, RF_BASE), m, c)
    lv = merged[ASSETS].replace(0, np.nan).ffill()
    simple = (lv / lv.shift(1) - 1).iloc[1:].clip(-P.RETURN_CAP, P.RETURN_CAP)
    m, c = annual(simple)
    est["simple instead of log returns"] = perf(max_sharpe(m, c, RF_BASE), m, c)
    c_lw = lw_cov(Rr)
    m_r = Rr.mean().values * 12
    lw = LedoitWolf().fit(Rr.values)
    est["Ledoit-Wolf covariance"] = perf(max_sharpe(m_r, c_lw, RF_BASE), m_r, c_lw) | {
        "shrinkage_intensity": float(lw.shrinkage_)}
    m_bs, phi = bayes_stein_mu(Rr)
    est["Bayes-Stein mean"] = perf(max_sharpe(m_bs, Rr.cov().values * 12, RF_BASE), m_bs,
                                   Rr.cov().values * 12) | {"shrinkage_phi": phi,
                                                            "mu": dict(zip(ASSETS, map(float, m_bs)))}
    est["Bayes-Stein mean + Ledoit-Wolf cov"] = perf(max_sharpe(m_bs, c_lw, RF_BASE), m_bs, c_lw)
    out["estimation_variants"] = est

    # 6. Block bootstrap of the optimal weights (circular blocks, real returns)
    rng = np.random.default_rng(P.RNG_SEED)
    x = Rr.values
    T = len(x)
    W, SR, cap_hits, floor_hits = [], [], 0, np.zeros(3)
    for _ in range(N_BOOT):
        starts = rng.integers(0, T, size=int(np.ceil(T / BLOCK)))
        idx = np.concatenate([(s + np.arange(BLOCK)) % T for s in starts])[:T]
        xb = x[idx]
        mb, cb = xb.mean(0) * 12, np.cov(xb, rowvar=False) * 12
        w = max_sharpe(mb, cb, RF_BASE, n_starts=2)
        W.append(w)
        SR.append((w @ mb - RF_BASE) / np.sqrt(w @ cb @ w))
        cap_hits += abs(w[0] - 0.70) < 1e-5
        floor_hits += np.abs(w - 0.02) < 1e-5
    W, SR = np.array(W), np.array(SR)
    q = [5, 25, 50, 75, 95]
    out["bootstrap"] = {
        "weights_percentiles": {a: dict(zip([f"p{p}" for p in q], np.percentile(W[:, i], q).round(4).tolist()))
                                for i, a in enumerate(ASSETS)},
        "weights_mean_resampled": describe(W.mean(0)),
        "resampled_weights_on_full_sample": perf(W.mean(0), m_r, Rr.cov().values * 12),
        "sharpe_in_resample_percentiles": dict(zip([f"p{p}" for p in q], np.percentile(SR, q).round(3).tolist())),
        "share_re_at_70pct_cap": float(cap_hits / N_BOOT),
        "share_at_2pct_floor": {a: float(f / N_BOOT) for a, f in zip(ASSETS, floor_hits)},
        "share_re_largest_weight": float((W.argmax(1) == 0).mean()),
    }

    # 7. In-sample benchmarks
    erc, erc_b = risk_parity(cov)
    mv, _ = min_var(cov)
    last = merged[ASSETS].iloc[-1].values
    bench = {"max-Sharpe (baseline)": base_w, "minimum variance": mv, "equal weight": np.full(3, 1 / 3),
             "risk parity (ERC, bounded)": erc_b, "risk parity (ERC, unbounded)": erc,
             "actual book Dec 2025": last / last.sum(),
             "actual book average": (merged[ASSETS].div(merged[ASSETS].sum(1), axis=0)).mean().values}
    out["benchmarks_in_sample"] = {k: perf(w, mu, cov) for k, w in bench.items()}

    # 8. Constrained QP frontier vs Monte Carlo cloud
    mv_ret = float(mv @ mu)
    max_ret = float(max(mu) * (1 - 0.04) + sorted(mu)[-2] * 0.02 + min(mu) * 0.02)  # feasible upper end
    pts = []
    for tgt in np.linspace(mv_ret, max_ret, 40):
        w, ok = min_var(cov, mu=mu, target=tgt)
        if ok:
            pts.append({"target": float(tgt), "volatility": float(np.sqrt(w @ cov @ w)),
                        "sharpe": float((tgt - RF_BASE) / np.sqrt(w @ cov @ w)), "weights": describe(w)})
    cloud, _ = P.simulate_efficient_frontier(pd.Series(mu, index=ASSETS), pd.DataFrame(cov, ASSETS, ASSETS), RF_BASE)
    fr_r = np.array([p["target"] for p in pts])
    fr_v = np.array([p["volatility"] for p in pts])
    on = cloud["return"] >= mv_ret
    gap = cloud.loc[on, "volatility"].values - np.interp(cloud.loc[on, "return"].values, fr_r, fr_v)
    out["qp_frontier"] = {
        "n_points": len(pts), "points": pts,
        "max_sharpe_on_frontier_grid": max(p["sharpe"] for p in pts),
        "tangency_from_optimiser": out["baseline"]["sharpe"],
        "mc_cloud_best_sharpe": float(cloud["sharpe"].max()),
        "mc_points_above_minvar_return": int(on.sum()),
        "mc_excess_vol_vs_frontier_pct_points": {"median": float(np.median(gap) * 100),
                                                 "p95": float(np.percentile(gap, 95) * 100),
                                                 "min": float(gap.min() * 100)},
        "mc_share_within_10bp_of_frontier": float((gap < 0.001).mean()),
    }

    # 9. Out-of-sample: expanding and rolling windows, monthly rebalancing
    shares = merged[ASSETS].div(merged[ASSETS].sum(1), axis=0).values
    simple_c = np.expm1(Rr.values)   # realised simple returns, clipped (model universe)
    simple_u = np.expm1(Ur.values)   # realised simple returns, unclipped
    strategies = ["max-Sharpe", "max-Sharpe LW+BS", "minimum variance", "risk parity (bounded)",
                  "equal weight", "actual book"]
    oos = {}
    for scheme in ["expanding", "rolling"]:
        weights = {s: [] for s in strategies}
        for t in range(OOS_START, T):
            win = Rr.iloc[(0 if scheme == "expanding" else t - ROLL_WINDOW):t]
            m_t, c_t = annual(win)
            mbs, _ = bayes_stein_mu(win)
            weights["max-Sharpe"].append(max_sharpe(m_t, c_t, RF_BASE, n_starts=3))
            weights["max-Sharpe LW+BS"].append(max_sharpe(mbs, lw_cov(win), RF_BASE, n_starts=3))
            weights["minimum variance"].append(min_var(c_t)[0])
            weights["risk parity (bounded)"].append(risk_parity(c_t)[1])
            weights["equal weight"].append(np.full(3, 1 / 3))
            weights["actual book"].append(shares[t])  # shares at month t = start of return t+1 in Rr indexing
        res = {}
        for s in strategies:
            Wt = np.array(weights[s])
            row = {"avg_weights": describe(Wt.mean(0))}
            for lab, sr in [("clipped", simple_c), ("unclipped", simple_u)]:
                rp = (Wt * sr[OOS_START:T]).sum(1)
                drift = Wt * (1 + sr[OOS_START:T]) / (1 + rp)[:, None]
                turn = np.r_[0.0, np.abs(Wt[1:] - drift[:-1]).sum(1)]
                for bp in COSTS_BP if lab == "clipped" else [0]:
                    net = rp - bp / 1e4 * turn
                    ann, vol = net.mean() * 12, net.std(ddof=1) * np.sqrt(12)
                    row[f"{lab}_{bp}bp"] = {"return": float(ann), "volatility": float(vol),
                                            "sharpe": float((ann - RF_BASE) / vol)}
                row[f"annual_turnover_{lab}"] = float(turn[1:].mean() * 12)
            res[s] = row
        oos[scheme] = res
    first, lastd = Rr.index[OOS_START], Rr.index[T - 1]
    out["out_of_sample"] = {"first_month": str(first.date()), "last_month": str(lastd.date()),
                            "n_months": T - OOS_START, "results": oos}

    # 10. Time variation: rolling correlations and split-sample optimum
    pairs = [(0, 1), (0, 2), (1, 2)]
    roll = {}
    for i, j in pairs:
        rc = Rr.iloc[:, i].rolling(24).corr(Rr.iloc[:, j]).dropna()
        roll[f"{ASSETS[i]}-{ASSETS[j]}"] = {"min": float(rc.min()), "median": float(rc.median()),
                                           "max": float(rc.max()), "last": float(rc.iloc[-1]),
                                           "full_sample": float(Rr.iloc[:, i].corr(Rr.iloc[:, j]))}
    half = T // 2
    split = {}
    for lab, part in [(f"{Rr.index[0]:%Y-%m}..{Rr.index[half-1]:%Y-%m}", Rr.iloc[:half]),
                      (f"{Rr.index[half]:%Y-%m}..{Rr.index[-1]:%Y-%m}", Rr.iloc[half:])]:
        m, c = annual(part)
        split[lab] = perf(max_sharpe(m, c, RF_BASE), m, c) | {"mu": dict(zip(ASSETS, map(float, m)))}
    vol_halves = {lab: dict(zip(ASSETS, (part.std() * np.sqrt(12)).round(4).tolist()))
                  for lab, part in [("first_half", Rr.iloc[:half]), ("second_half", Rr.iloc[half:])]}
    out["time_variation"] = {"rolling_24m_correlation": roll, "split_sample": split, "volatility_by_half": vol_halves}

    (P.OUTPUT_DIR / f"{args.tag}_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float),
                                                   encoding="utf-8")
    print(report(out))
    (P.OUTPUT_DIR / f"{args.tag}_report.txt").write_text(report(out), encoding="utf-8")


def report(o):
    L = []
    f = lambda d: f"RE {d['weights'][ASSETS[0]]*100:6.2f}  Auto {d['weights'][ASSETS[1]]*100:6.2f}  " \
                  f"Eq {d['weights'][ASSETS[2]]*100:6.2f} | E[R] {d['return']*100:6.2f}  " \
                  f"vol {d['volatility']*100:5.2f}  SR {d['sharpe']:6.3f}"
    L.append("BASELINE  " + f(o["baseline"]) + f"  binding={o['baseline']['binding']}")
    for sec in ["rf_grid", "clip_grid", "gap_variants", "estimation_variants", "benchmarks_in_sample"]:
        L.append(f"\n== {sec}")
        for k, d in o[sec].items():
            L.append(f"{k:<38} " + f(d) + (f"  {d['binding']}" if "binding" in d else ""))
    L.append("\n== cap_floor_grid")
    for d in o["cap_floor_grid"]:
        L.append(f"cap {d['re_cap']:.2f} floor {d['floor']:.2f}  " + f(d) + f"  {d['binding']}")
    L.append("\n== bootstrap\n" + json.dumps(o["bootstrap"], indent=1, ensure_ascii=False))
    q = o["qp_frontier"]
    L.append("\n== qp_frontier\n" + json.dumps({k: v for k, v in q.items() if k != "points"}, indent=1))
    oo = o["out_of_sample"]
    L.append(f"\n== out_of_sample {oo['first_month']}..{oo['last_month']} ({oo['n_months']} months)")
    for scheme, res in oo["results"].items():
        L.append(f"-- {scheme}")
        for s, r in res.items():
            c0, u0 = r["clipped_0bp"], r["unclipped_0bp"]
            L.append(f"{s:<24} avgW {r['avg_weights']}  clipped R {c0['return']*100:6.2f} vol "
                     f"{c0['volatility']*100:5.2f} SR {c0['sharpe']:6.3f} | unclipped R {u0['return']*100:6.2f} vol "
                     f"{u0['volatility']*100:5.2f} SR {u0['sharpe']:6.3f} | turnover/yr {r['annual_turnover_clipped']:.3f}"
                     f" | SR@50bp {r['clipped_50bp']['sharpe']:.3f}")
    L.append("\n== time_variation\n" + json.dumps(o["time_variation"], indent=1, ensure_ascii=False))
    return "\n".join(L)


if __name__ == "__main__":
    main()
