"""AP7: write every number the revised manuscript reports as LaTeX, straight from the result files.

The manuscript \\input{}s these files and uses the macros in results_macros.tex, so no reported number is
typed by hand. Re-run after any change to the analysis.

Reads: data/data_corrected.xlsx, outputs/{d6_baseline,d6_separate,ap4_d6}_results.json
Writes: tables/*.tex

Usage (from this folder):  python -P make_tex_tables.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import robustness as RB  # noqa: E402

WS = Path(__file__).resolve().parents[1]
OUT = WS / "tables"
J = lambda tag: json.loads((WS / "outputs" / f"{tag}_results.json").read_text(encoding="utf-8"))
BASE, SEP, AP4 = J("d6_baseline"), J("d6_separate"), J("ap4_d6")
A = RB.ASSETS
SHORT = {"Immobilière": "Real estate", "Automobile": "Automobile", "Equipement": "Equipment + raw mat."}
p2 = lambda x: f"{x * 100:.2f}"
p1 = lambda x: f"{x * 100:.1f}"
f3 = lambda x: f"{x:.3f}"


def sci(x):
    m, e = f"{x:.1e}".split("e")
    return f"${m}\\times 10^{{{int(e)}}}$"


def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8")


def tabular(cols, header, rows, note=None):
    body = [f"\\begin{{tabular}}{{{cols}}}", "\\toprule", header + " \\\\", "\\midrule"]
    body += [" & ".join(r) + " \\\\" for r in rows]
    body += ["\\bottomrule", "\\end{tabular}"]
    if note:
        body += [f"\\par\\smallskip\\parbox{{\\linewidth}}{{\\footnotesize {note}}}"]
    return "\n".join(body) + "\n"


def wrow(label, d, extra=()):
    w = d["weights"]
    return [label, *(p2(w[a]) for a in A), p2(d["return"]), p2(d["volatility"]), f"{d['sharpe']:.2f}", *extra]


WHEAD = "& RE & Auto & Equip+Raw & Growth & Vol. & Ratio"


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- data table (Table 1) ------------------------------------------------
    raw = pd.read_excel(RB.DATA_CORR, sheet_name="Feuil1")
    log = pd.read_excel(RB.DATA_CORR, sheet_name="corrections_log")
    corrected = {(r["Date"], r["column"]) for _, r in log.iterrows() if r["method"] == "value printed in BKAM report"}
    est = set(raw.loc[raw["flag"].eq("estimated"), "Date"])
    m = RB.load_murabaha()
    lv = m[A].replace(0, np.nan)
    lr = np.log(lv / lv.shift(1)) * 100
    sh = m[A].div(m[A].sum(1), axis=0) * 100
    rows = []
    for i, (d, r) in enumerate(raw.iterrows()):
        date = r["Date"]
        cell = lambda col, v: f"{int(round(v)):,}" + ("$^{*}$" if (date, col) in corrected else "")
        eq = r["Equipement"] + r["Matieres Premieres"]
        eq_s = f"{int(round(eq)):,}" + ("$^{*}$" if (date, "Equipement") in corrected else "")
        rm = f"{int(round(r['Matieres Premieres'])):,}" if r["Matieres Premieres"] else "--"
        per = date + ("$^{\\dagger}$" if date in est else "")
        rets = ["--"] * 3 if i == 0 else [f"{lr.iloc[i][a]:.2f}" for a in A]
        rows.append(" & ".join([per, f"{int(round(r['Totale'])):,}", cell(A[0], r[A[0]]), cell(A[1], r[A[1]]), eq_s, rm,
                                *(f"{sh.iloc[i][a]:.2f}" for a in A), *rets]) + " \\\\")
    write("tab_dataset_rows.tex", "\n".join(rows) + "\n")

    # ---- covariance (Table 2) ------------------------------------------------
    cov = np.array(BASE["cov_annual"])
    corr = np.array(BASE["corr"])
    cd = BASE["covariance_diagnostics"]
    lab = [SHORT[a] for a in A]
    rows = [[f"\\textbf{{{lab[i]}}}"] + [(f"{cov[i, j]:.6f}" if j >= i else f"({corr[i, j]:.2f})") for j in range(3)]
            for i in range(3)]
    write("tab_cov.tex", tabular("lccc", " & " + " & ".join(f"\\textbf{{{x}}}" for x in lab), rows,
          "Upper triangle and diagonal: annualized covariances of monthly log-growth rates (clipped at $\\pm10\\%$, "
          "77 observations, $\\times 12$). Lower triangle, in parentheses: correlations. Eigenvalues: "
          + ", ".join(f"{e:.5f}" for e in cd["eigenvalues"]) + f"; condition number {cd['condition_number']:.1f}; "
          "the matrix is positive definite."))

    # ---- baseline (Table 3) --------------------------------------------------
    opt, mu = BASE["optimal"], BASE["expected_returns"]
    sig = np.sqrt(np.diag(cov))
    rows = [[lab[i], p2(mu[a]), p2(sig[i]), p2(opt["weights"][a])] for i, a in enumerate(A)]
    rows.append(["\\textbf{Portfolio}", p2(opt["return"]), p2(opt["volatility"]), "100.00"])
    sv, kk = BASE["solver"], BASE["kkt"]
    write("tab_baseline.tex", tabular("lccc", "\\textbf{Segment} & \\textbf{Growth (\\%)} & \\textbf{Volatility (\\%)} "
          "& \\textbf{Weight (\\%)}", rows,
          f"Growth-to-volatility ratio at $R_f = 4.5\\%$: {opt['sharpe']:.3f}. SLSQP converged in {sv['nit']} iterations "
          f"({sv['nfev']} function evaluations). No bound is active (smallest slack {kk['min_bound_slack']*100:.2f} "
          f"percentage points, to the 70\\% cap); largest KKT stationarity residual "
          + sci(max(abs(x) for x in kk["stationarity_residual_free_assets"])) + "."))

    # ---- clip grid (Table 4) -------------------------------------------------
    rows = [wrow(k.replace("±", "$\\pm$").replace("%", "\\%"), d,
                 [str(d["n_clipped"][A[2]]), p1(d["mu"][A[2]]), ", ".join(d["binding"]).replace("Immobilière@cap", "RE cap") or "none"])
            for k, d in AP4["clip_grid"].items()]
    write("tab_clip.tex", tabular("lccccccccl", "\\textbf{Clip} " + WHEAD + " & $n_{\\text{clip}}$ & $\\mu_{\\text{Eq}}$ & Binding",
          rows, "Weights, growth and volatility in \\%. $n_{\\text{clip}}$: equipment returns (of 77) outside the band; "
          "$\\mu_{\\text{Eq}}$: annualized equipment growth after clipping. All other settings as in the baseline."))

    # ---- bootstrap (Table 5) -------------------------------------------------
    bw = AP4["bootstrap"]["weights_percentiles"]
    rows = [[f"{p[1:]}th", *(p2(bw[a][p]) for a in A)] for p in ["p5", "p25", "p50", "p75", "p95"]]
    mw = AP4["bootstrap"]["weights_mean_resampled"]
    rows.append(["Mean (resampled)", *(p2(mw[a]) for a in A)])
    bsr = AP4["bootstrap"]["sharpe_in_resample_percentiles"]
    write("tab_bootstrap.tex", tabular("lccc", "\\textbf{Percentile} & RE & Auto & Equip+Raw", rows,
          f"Circular block bootstrap, block length 6, {AP4['settings']['n_boot']:,} resamples of the 77 monthly returns; "
          "the model is re-estimated and re-optimized in each resample. Real estate is the largest weight in "
          f"{AP4['bootstrap']['share_re_largest_weight']*100:.1f}\\% of resamples and at its 70\\% cap in "
          f"{AP4['bootstrap']['share_re_at_70pct_cap']*100:.1f}\\%. In-resample ratio, 5th--95th percentile: "
          f"{bsr['p5']:.2f}--{bsr['p95']:.2f}."))

    # ---- out of sample (Table 6, appendix rolling) ----------------------------
    oo = AP4["out_of_sample"]
    names = {"max-Sharpe": "Max-ratio (baseline)", "max-Sharpe LW+BS": "Max-ratio, shrinkage", "minimum variance":
             "Minimum variance", "risk parity (bounded)": "Risk parity", "equal weight": "Equal weight",
             "actual book": "Observed sector mix"}
    for scheme in ["expanding", "rolling"]:
        rows = []
        for s, r in oo["results"][scheme].items():
            c0, w = r["clipped_0bp"], r["avg_weights"]
            rows.append([names[s], " / ".join(p1(w[a]) for a in A), p2(c0["return"]), p2(c0["volatility"]),
                         f"{c0['sharpe']:.2f}", f"{r['unclipped_0bp']['sharpe']:.2f}", f"{r['annual_turnover_clipped']:.3f}",
                         f"{r['clipped_50bp']['sharpe']:.2f}"])
        write(f"tab_oos_{scheme}.tex", tabular("llcccccc", "\\textbf{Strategy} & Avg.\\ weights (\\%) & Growth & Vol. & "
              "Ratio & Ratio$^{u}$ & Turnover & Ratio$_{50}$", rows,
              f"{scheme.capitalize()} estimation window ({'from the first 36 returns' if scheme == 'expanding' else '36 months'}), "
              f"monthly re-optimization, evaluation {oo['first_month'][:7]} to {oo['last_month'][:7]} ({oo['n_months']} months). "
              "Growth and volatility: annualized realized balance growth of the allocation (\\%), using clipped segment "
              "growth; Ratio$^{u}$ uses unclipped growth. Turnover: average annual one-way turnover after drift. "
              "Ratio$_{50}$: ratio net of a 50\\,bp cost per unit of turnover. All ratios use $R_f = 4.5\\%$."))

    # ---- appendix grids -----------------------------------------------------------
    rows = [wrow(k.replace("%", "\\%"), d, [p2(d["rf"])]) for k, d in AP4["rf_grid"].items()]
    write("tab_rf.tex", tabular("lccccccc", "\\textbf{$R_f$ setting} " + WHEAD + " & $R_f$ (\\%)", rows))
    seen, rows = set(), []
    for d in AP4["cap_floor_grid"]:
        if d["re_cap"] in seen:
            continue
        seen.add(d["re_cap"])
        same = all(abs(x["sharpe"] - d["sharpe"]) < 1e-9 for x in AP4["cap_floor_grid"] if x["re_cap"] == d["re_cap"])
        rows.append(wrow(f"{d['re_cap']*100:.0f}\\%", d, [", ".join(d["binding"]).replace("Immobilière@cap", "RE cap") or "none",
                                                          "yes" if same else "no"]))
    write("tab_capfloor.tex", tabular("lccccccll", "\\textbf{RE cap} " + WHEAD + " & Binding & Same for floors 0--5\\%", rows))
    write("tab_gap.tex", tabular("lcccccc", "\\textbf{Gap months} " + WHEAD,
          [wrow({"main": "BAM monthly variation (baseline)", "low": "Lower end of rounding interval",
                 "high": "Upper end of rounding interval", "log_linear_interpolation": "Log-linear interpolation"}[k], d)
           for k, d in AP4["gap_variants"].items()]))
    lbl = {"v2 first-row zero kept (78 rows)": "Original code convention (78 rows)", "simple instead of log returns":
           "Simple instead of log growth", "Ledoit-Wolf covariance": "Ledoit--Wolf covariance", "Bayes-Stein mean":
           "Bayes--Stein mean", "Bayes-Stein mean + Ledoit-Wolf cov": "Bayes--Stein mean + Ledoit--Wolf cov."}
    write("tab_estimation.tex", tabular("lcccccc", "\\textbf{Estimator} " + WHEAD,
          [wrow("Baseline", AP4["baseline"])] + [wrow(lbl[k], d) for k, d in AP4["estimation_variants"].items()]))
    bl = {"max-Sharpe (baseline)": "Max-ratio (baseline)", "minimum variance": "Minimum variance", "equal weight":
          "Equal weight", "risk parity (ERC, bounded)": "Risk parity (ERC)", "actual book Dec 2025": "Observed mix, Dec 2025",
          "actual book average": "Observed mix, sample average"}
    write("tab_bench_insample.tex", tabular("lcccccc", "\\textbf{Portfolio} " + WHEAD,
          [wrow(bl[k], d) for k, d in AP4["benchmarks_in_sample"].items() if k in bl]))
    tv = AP4["time_variation"]
    write("tab_rollcorr.tex", tabular("lccccc", "\\textbf{Pair} & Min & Median & Max & Dec 2025 & Full sample",
          [[k.replace("Immobilière", "RE").replace("Automobile", "Auto").replace("Equipement", "Equip+Raw"),
            *(f"{d[x]:.2f}" for x in ["min", "median", "max", "last", "full_sample"])]
           for k, d in tv["rolling_24m_correlation"].items()]))
    write("tab_split.tex", tabular("lcccccc", "\\textbf{Sub-period} " + WHEAD,
          [wrow(k.replace("..", "--"), d) for k, d in tv["split_sample"].items()]))
    so = SEP["optimal"]
    A4 = ["Immobilière", "Automobile", "Equipement", "Matieres Premieres"]
    write("tab_fourasset.tex", tabular("lccc", "& \\textbf{Three segments (baseline)} & \\textbf{Four segments} & ",
          [[x, y, z, ""] for x, y, z in [
              ("Real estate", p2(opt["weights"][A[0]]), p2(so["weights"][A4[0]])),
              ("Automobile", p2(opt["weights"][A[1]]), p2(so["weights"][A4[1]])),
              ("Equipment", p2(opt["weights"][A[2]]) + " (incl. raw mat.)", p2(so["weights"][A4[2]])),
              ("Raw materials", "--", p2(so["weights"][A4[3]]) + " (floor)"),
              ("Growth / volatility", f"{p2(opt['return'])} / {p2(opt['volatility'])}", f"{p2(so['return'])} / {p2(so['volatility'])}"),
              ("Ratio", f"{opt['sharpe']:.3f}", f"{so['sharpe']:.3f}"),
              ("Condition number of $\\Sigma$", f"{BASE['covariance_diagnostics']['condition_number']:.1f}",
               f"{SEP['covariance_diagnostics']['condition_number']:.1f}")]]))

    # ---- in-text macros ---------------------------------------------------------
    clip, oe = AP4["clip_grid"], oo["results"]["expanding"]
    eqw = [d["weights"][A[2]] for d in clip.values()]
    rfw = [d["weights"][A[0]] for k, d in AP4["rf_grid"].items() if d["rf"] <= 0.045 + 1e-12]
    sp = tv["split_sample"]
    k1, k2 = list(sp)
    mac = {
        "WRE": p2(opt["weights"][A[0]]), "WAuto": p2(opt["weights"][A[1]]), "WEq": p2(opt["weights"][A[2]]),
        "PGrowth": p2(opt["return"]), "PVol": p2(opt["volatility"]), "PRatio": f"{opt['sharpe']:.2f}",
        "MuRE": p2(mu[A[0]]), "MuAuto": p2(mu[A[1]]), "MuEq": p2(mu[A[2]]),
        "VolRE": p2(sig[0]), "VolAuto": p2(sig[1]), "VolEq": p2(sig[2]),
        "CorrREAuto": f"{corr[0, 1]:.2f}", "CorrREEq": f"{corr[0, 2]:.2f}", "CorrAutoEq": f"{corr[1, 2]:.2f}",
        "CondNo": f"{cd['condition_number']:.1f}", "Slack": f"{kk['min_bound_slack']*100:.1f}", "Iters": str(sv["nit"]),
        "NClipEq": str(BASE["winsorisation_counts"][A[2]]["upper"] + BASE["winsorisation_counts"][A[2]]["lower"]),
        "NClipAuto": str(BASE["winsorisation_counts"][A[1]]["upper"] + BASE["winsorisation_counts"][A[1]]["lower"]),
        "RfRaw": p2(BASE["rf_info"]["rf_raw_unclipped"]), "RfMean": p2(BASE["rf_info"]["rf_raw_mean_instead_of_median"]),
        "RfREmin": p1(min(rfw)), "RfREmax": p1(max(rfw)),
        "ClipEqMin": p1(min(eqw)), "ClipEqMax": p1(max(eqw)),
        "BRElo": p1(bw[A[0]]["p5"]), "BREhi": p1(bw[A[0]]["p95"]), "BEqlo": p1(bw[A[2]]["p5"]), "BEqhi": p1(bw[A[2]]["p95"]),
        "BAutolo": p1(bw[A[1]]["p5"]), "BAutohi": p1(bw[A[1]]["p95"]),
        "BRElargest": p1(AP4["bootstrap"]["share_re_largest_weight"]), "BREcap": p1(AP4["bootstrap"]["share_re_at_70pct_cap"]),
        "LWRE": p1(AP4["estimation_variants"]["Ledoit-Wolf covariance"]["weights"][A[0]]),
        "OOSMonths": str(oo["n_months"]), "OOSGrowthMR": p1(oe["max-Sharpe"]["clipped_0bp"]["return"]),
        "OOSGrowthBook": p1(oe["actual book"]["clipped_0bp"]["return"]),
        "OOSRatioMR": f"{oe['max-Sharpe']['clipped_0bp']['sharpe']:.2f}",
        "OOSRatioMV": f"{oe['minimum variance']['clipped_0bp']['sharpe']:.2f}",
        "OOSRatioRP": f"{oe['risk parity (bounded)']['clipped_0bp']['sharpe']:.2f}",
        "OOSRatioEW": f"{oe['equal weight']['clipped_0bp']['sharpe']:.2f}",
        "OOSRatioBook": f"{oe['actual book']['clipped_0bp']['sharpe']:.2f}",
        "OOSTurnMR": f"{oe['max-Sharpe']['annual_turnover_clipped']*100:.0f}",
        "OOSTurnBook": f"{oe['actual book']['annual_turnover_clipped']*100:.1f}",
        "ShareREDec": p1(m[A[0]].iloc[-1] / m[A].iloc[-1].sum()),
        "ShareREstart": p1(m[A[0]].iloc[0] / m[A].iloc[0].sum()),
        "SplitMuEqA": p1(sp[k1]["mu"][A[2]]), "SplitMuEqB": p1(sp[k2]["mu"][A[2]]),
        "SepWRE": p2(so["weights"][A4[0]]), "SepWRaw": p2(so["weights"][A4[3]]),
        "SepEta": f"{SEP['kkt']['implied_lower_bound_multipliers'][A4[3]]:.3f}",
        "TotalStart": f"{m['Totale'].iloc[0]/1e6:.1f}", "TotalEnd": f"{m['Totale'].iloc[-1]/1e6:.1f}",
        "MCBest": f"{AP4['qp_frontier']['mc_cloud_best_sharpe']:.4f}", "QPBest": f"{AP4['qp_frontier']['tangency_from_optimiser']:.4f}",
        "MCWithin": p1(AP4["qp_frontier"]["mc_share_within_10bp_of_frontier"]),
    }
    write("results_macros.tex", "% Generated by code/make_tex_tables.py from outputs/*.json. Do not edit.\n"
          + "\n".join(f"\\newcommand{{\\res{k}}}{{{v}}}" for k, v in mac.items()) + "\n")
    print(f"wrote {len(list(OUT.glob('*.tex')))} files; macros: {len(mac)}")
    tot = (m["Totale"] - m[A].sum(1)).abs().max()
    print("max |Total - sum of segments| (thousand MAD):", tot)


if __name__ == "__main__":
    main()
