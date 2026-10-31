"""De-Colab'd copy of murabaha_portfolio_optimization_v2.ipynb (AP1), plus read-only diagnostics (AP2).

The data, return, Rf, optimisation and Monte Carlo logic is copied from the notebook unchanged
(same constants, same SLSQP call, same seed). Removed: Colab/Drive cells, pip install,
plotting (matplotlib is not installed here). Added: diagnostics that the notebook did not print.

Reads (never writes): data/raw/{data.xlsx, 4CPBFP.xlsx}
Writes: outputs/ap2_results.json, ap2_report.txt

Usage (from this folder):  python -P pipeline.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "data.xlsx"
BFP_PATH = ROOT / "data" / "raw" / "4CPBFP.xlsx"
OUTPUT_DIR = ROOT / "outputs"

# --- Constants copied from the notebook ------------------------------------
ASSETS = ["Immobilière", "Automobile", "Equipement", "Matieres Premieres"]
MONTHS_PER_YEAR = 12
RETURN_CAP = 0.10
RF_TRAILING_MONTHS = 24
RF_MIN = 0.020
RF_MAX = 0.045
N_FRONTIER_PORTFOLIOS = 8_000
RNG_SEED = 42

# Values printed in the notebook's stored outputs (target of the reproduction check).
NOTEBOOK_STORED = {
    "n_months": 77,
    "expected_returns": {"Immobilière": 0.2322, "Automobile": 0.2210, "Equipement": 0.6212,
                         "Matieres Premieres": -0.0064},
    "rf": 0.0450,
    "weights": {"Immobilière": 0.3226, "Automobile": 0.1211, "Equipement": 0.5363,
                "Matieres Premieres": 0.0200},
    "return": 0.4347,
    "volatility": 0.1042,
    "sharpe": 3.7391,
    "cov_diag": {"Immobilière": 0.007411, "Automobile": 0.009085, "Equipement": 0.026451,
                 "Matieres Premieres": 0.000692},
}


# --- Section 3 of the notebook: loading and merging ------------------------
def load_murabaha_data(path):
    df = pd.read_excel(path, sheet_name="Feuil1")
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m")
    df = df.set_index("Date").sort_index()
    df = df.dropna(subset=["Totale"])
    return df


def load_and_transpose_balance_sheet(path):
    raw = pd.read_excel(path, sheet_name="CP_BANUQ_PAR", header=2, index_col=0)
    raw = raw.dropna(how="all")
    raw.index = raw.index.astype(str).str.strip()
    raw = raw[~raw.index.duplicated(keep="first")]
    bs = raw.T
    bs.index = pd.to_datetime(bs.index)
    bs.index.name = "Date"
    bs.columns = [re.sub(r"\d+$", "", str(c)).strip() for c in bs.columns]
    bs = bs.apply(pd.to_numeric, errors="coerce")
    return bs.sort_index()


def merge_datasets(murabaha, balance_sheet):
    m = murabaha.copy()
    b = balance_sheet.copy()
    m.index = m.index.to_period("M")
    b.index = b.index.to_period("M")
    merged = m.join(b, how="inner", rsuffix="_bs")
    merged.index = merged.index.to_timestamp()
    merged = merged.sort_index()
    merged = merged.ffill().fillna(0.0)
    return merged


# --- Section 4: returns, annualisation, Rf ---------------------------------
def compute_returns(merged, return_cap=RETURN_CAP):
    levels = merged[ASSETS].replace(0, np.nan).ffill()
    returns = np.log(levels / levels.shift(1))
    returns = returns.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    unclipped = returns.copy()
    returns = returns.clip(lower=-return_cap, upper=return_cap)
    return returns, unclipped


def annualise_return_and_covariance(monthly_returns):
    return monthly_returns.mean() * MONTHS_PER_YEAR, monthly_returns.cov() * MONTHS_PER_YEAR


def estimate_shariah_reference_rate(merged, trailing_months=RF_TRAILING_MONTHS, rf_min=RF_MIN, rf_max=RF_MAX):
    """Same estimator as the notebook; also returns the pre-clip value and the window."""
    candidate_columns = ["Dépôts d'investissement", "Depots d'investissement", "Dépôts d’investissement"]
    col = next((c for c in candidate_columns if c in merged.columns), None)
    if col is None:
        return float((rf_min + rf_max) / 2.0), {"column": None}
    psia = merged[col].replace(0, np.nan).ffill()
    log_growth = np.log(psia / psia.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
    window = min(trailing_months, len(log_growth))
    trailing_window = log_growth.tail(window)
    rf_raw = float(trailing_window.median() * MONTHS_PER_YEAR)
    rf = float(np.clip(rf_raw, rf_min, rf_max))
    info = {
        "column": col,
        "rf_raw_unclipped": rf_raw,
        "window_start": str(trailing_window.index[0].date()),
        "window_end": str(trailing_window.index[-1].date()),
        "window_n": int(window),
        "rf_raw_mean_instead_of_median": float(trailing_window.mean() * MONTHS_PER_YEAR),
        "rf_raw_full_sample_median": float(log_growth.median() * MONTHS_PER_YEAR),
    }
    return rf, info


# --- Section 6: optimisation ------------------------------------------------
def portfolio_performance(weights, expected_returns, cov_matrix):
    port_return = float(np.dot(weights, expected_returns))
    port_vol = float(np.sqrt(weights.T @ cov_matrix @ weights))
    return port_return, port_vol


def negative_sharpe_ratio(weights, expected_returns, cov_matrix, rf):
    port_return, port_vol = portfolio_performance(weights, expected_returns, cov_matrix)
    if port_vol == 0:
        return 0.0
    return -(port_return - rf) / port_vol


def optimise_max_sharpe(expected_returns, cov_matrix, rf):
    n_assets = len(expected_returns)
    mu = expected_returns.values
    cov = cov_matrix.values
    bounds = [(0.02, 0.70)] + [(0.02, 1.00)] * (n_assets - 1)
    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    x0 = np.array([1.0 / n_assets] * n_assets)
    result = minimize(negative_sharpe_ratio, x0, args=(mu, cov, rf), method="SLSQP",
                      bounds=bounds, constraints=constraints, options={"maxiter": 1000, "ftol": 1e-12})
    if not result.success:
        raise RuntimeError(f"Portfolio optimisation failed to converge: {result.message}")
    w = result.x
    ret, vol = portfolio_performance(w, mu, cov)
    return {"weights": pd.Series(w, index=expected_returns.index), "return": ret, "volatility": vol,
            "sharpe": (ret - rf) / vol, "raw_result": result, "bounds": bounds}


# --- Section 7: Monte Carlo cloud (same sampler and seed) ------------------
def simulate_efficient_frontier(expected_returns, cov_matrix, rf, n_portfolios=N_FRONTIER_PORTFOLIOS, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    n_assets = len(expected_returns)
    mu = expected_returns.values
    cov = cov_matrix.values
    lower_bounds = np.array([0.02] + [0.02] * (n_assets - 1))
    upper_bounds = np.array([0.70] + [1.00] * (n_assets - 1))
    records, attempts = [], 0
    while len(records) < n_portfolios and attempts < n_portfolios * 50:
        attempts += 1
        w = rng.dirichlet(np.ones(n_assets))
        if np.all(w >= lower_bounds) and np.all(w <= upper_bounds):
            ret, vol = portfolio_performance(w, mu, cov)
            records.append((vol, ret, (ret - rf) / vol if vol > 0 else np.nan, *w))
    columns = ["volatility", "return", "sharpe"] + list(expected_returns.index)
    return pd.DataFrame(records, columns=columns), attempts


# --- Diagnostics added for the audit (not in the notebook) -----------------
def kkt_check(opt, mu, cov, rf, tol=1e-6):
    """First-order conditions for min f(w) = -SR(w) s.t. sum w = 1, l <= w <= u.

    Stationarity: grad f + nu * 1 - lam_lower + lam_upper = 0, with lam >= 0 only on active bounds.
    nu is estimated from the free (inactive) assets; multipliers on active bounds are then implied.
    """
    w = opt["weights"].values
    ret, vol = portfolio_performance(w, mu, cov)
    grad = -((mu * vol) - (ret - rf) * (cov @ w) / vol) / vol ** 2  # analytic gradient of -SR
    lo = np.array([b[0] for b in opt["bounds"]])
    hi = np.array([b[1] for b in opt["bounds"]])
    at_lo = np.abs(w - lo) < tol
    at_hi = np.abs(w - hi) < tol
    free = ~(at_lo | at_hi)
    nu = float(-grad[free].mean()) if free.any() else float("nan")
    resid = grad + nu
    return {
        "gradient_neg_sharpe": grad.tolist(),
        "nu_budget_multiplier": nu,
        "stationarity_residual_free_assets": resid[free].tolist(),
        "active_lower_bounds": [ASSETS[i] for i in np.where(at_lo)[0]],
        "active_upper_bounds": [ASSETS[i] for i in np.where(at_hi)[0]],
        "implied_lower_bound_multipliers": {ASSETS[i]: float(resid[i]) for i in np.where(at_lo)[0]},
        "implied_upper_bound_multipliers": {ASSETS[i]: float(-resid[i]) for i in np.where(at_hi)[0]},
        "budget_residual": float(w.sum() - 1.0),
        "min_bound_slack": float(min((w - lo).min(), (hi - w).min())),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_PATH, help="Murabaha workbook (sheet Feuil1)")
    ap.add_argument("--tag", default="ap2", help="prefix for output files")
    ap.add_argument("--merge-raw", action="store_true",
                    help="decision D3(a): treat Equipement + Matieres Premieres as one asset (3-asset model)")
    ap.add_argument("--drop-first-zero", action="store_true",
                    help="decision D6: drop the undefined first return that v2 fills with 0 (77 returns)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    murabaha = load_murabaha_data(args.data)
    if args.merge_raw:
        # BAM split raw materials out of equipment in Sep 2024 (restated Dec-23 sums back exactly),
        # so the sum is the series that is consistent over the whole sample.
        global ASSETS
        murabaha["Equipement"] = murabaha["Equipement"] + murabaha["Matieres Premieres"]
        ASSETS = ["Immobilière", "Automobile", "Equipement"]
    balance_sheet = load_and_transpose_balance_sheet(BFP_PATH)
    merged = merge_datasets(murabaha, balance_sheet)

    monthly_returns, unclipped = compute_returns(merged)
    if args.drop_first_zero:
        monthly_returns, unclipped = monthly_returns.iloc[1:], unclipped.iloc[1:]
    expected_returns, cov_matrix = annualise_return_and_covariance(monthly_returns)
    rf, rf_info = estimate_shariah_reference_rate(merged)
    mu_s, cov_df = expected_returns[ASSETS], cov_matrix.loc[ASSETS, ASSETS]
    optimal = optimise_max_sharpe(mu_s, cov_df, rf)
    frontier, attempts = simulate_efficient_frontier(mu_s, cov_df, rf)

    mu, cov = mu_s.values, cov_df.values
    eig = np.linalg.eigvalsh(cov)
    res = optimal["raw_result"]
    best_mc = frontier.loc[frontier["sharpe"].idxmax()]
    clip_counts = {a: {"upper": int((unclipped[a] > RETURN_CAP).sum()),
                       "lower": int((unclipped[a] < -RETURN_CAP).sum()),
                       "exact_zero": int((unclipped[a].iloc[0 if args.drop_first_zero else 1:] == 0).sum())}
                   for a in ASSETS}

    out = {
        "inputs": {"data": Path(args.data).as_posix(), "bfp": BFP_PATH.relative_to(ROOT).as_posix(),
                   "versions": {"python": sys.version.split()[0], "numpy": np.__version__,
                                "pandas": pd.__version__, "scipy": __import__("scipy").__version__}},
        "sample": {"n_months": len(merged), "first": str(merged.index.min().date()),
                   "last": str(merged.index.max().date()), "n_returns": len(merged) - 1,
                   "rows_used_for_mu_cov": len(monthly_returns)},
        "expected_returns": mu_s.to_dict(),
        "expected_returns_unclipped": (unclipped[ASSETS].mean() * MONTHS_PER_YEAR).to_dict(),
        "cov_annual": cov_df.round(10).values.tolist(),
        "corr": monthly_returns[ASSETS].corr().round(6).values.tolist(),
        "rf": rf, "rf_info": rf_info,
        "optimal": {"weights": optimal["weights"].to_dict(), "return": optimal["return"],
                    "volatility": optimal["volatility"], "sharpe": optimal["sharpe"]},
        "solver": {"success": bool(res.success), "status": int(res.status), "message": str(res.message),
                   "nit": int(res.nit), "nfev": int(res.nfev), "fun": float(res.fun)},
        "covariance_diagnostics": {"eigenvalues": eig.tolist(), "positive_definite": bool(eig.min() > 0),
                                   "condition_number": float(eig.max() / eig.min())},
        "kkt": kkt_check(optimal, mu, cov, rf),
        "winsorisation_counts": clip_counts,
        "monte_carlo": {"n_kept": len(frontier), "attempts": attempts,
                        "best_sharpe": float(best_mc["sharpe"]),
                        "best_weights": best_mc[ASSETS].to_dict(),
                        "max_return": float(frontier["return"].max()),
                        "min_volatility": float(frontier["volatility"].min())},
        "notebook_stored": NOTEBOOK_STORED,
    }

    # Reproduction check at the notebook's printed precision.
    checks = []
    for a in ASSETS:
        checks.append((f"mu {a}", round(mu_s[a], 4), NOTEBOOK_STORED["expected_returns"][a]))
        checks.append((f"w {a}", round(optimal["weights"][a], 4), NOTEBOOK_STORED["weights"][a]))
        checks.append((f"cov[{a},{a}]", round(cov_df.loc[a, a], 6), NOTEBOOK_STORED["cov_diag"][a]))
    checks += [("n_months", len(merged), NOTEBOOK_STORED["n_months"]),
               ("rf", round(rf, 4), NOTEBOOK_STORED["rf"]),
               ("return", round(optimal["return"], 4), NOTEBOOK_STORED["return"]),
               ("volatility", round(optimal["volatility"], 4), NOTEBOOK_STORED["volatility"]),
               ("sharpe", round(optimal["sharpe"], 4), NOTEBOOK_STORED["sharpe"])]
    out["reproduction_check"] = [{"item": k, "reproduced": v, "notebook": s, "match": bool(abs(v - s) < 1e-9)}
                                 for k, v, s in checks]

    (OUTPUT_DIR / f"{args.tag}_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [f"{c['item']:<32} reproduced={c['reproduced']:<12} notebook={c['notebook']:<12} "
             f"{'OK' if c['match'] else 'DIFF'}" for c in out["reproduction_check"]]
    report = "\n".join(lines) + "\n\n" + json.dumps({k: out[k] for k in (
        "sample", "rf_info", "solver", "covariance_diagnostics", "kkt", "winsorisation_counts",
        "expected_returns_unclipped", "monte_carlo", "inputs")}, indent=2, ensure_ascii=False)
    (OUTPUT_DIR / f"{args.tag}_report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
