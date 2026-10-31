"""AP5: regenerate the manuscript figures from the final baseline (corrected data, merged, 77 returns; see 17).

File names match the figures referenced by the manuscript.
The methodology diagram is TikZ in main.tex and is not generated here.

Reads: data/data_corrected.xlsx, outputs/d6_baseline_results.json, outputs/ap4_d6_results.json
Writes: figures/<name>.pdf (vector) and <name>.png (300 dpi)

Usage (from this folder):  python -P make_figures.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P  # noqa: E402
import robustness as RB  # noqa: E402

WS = P.ROOT
FIG = WS / "figures"
BASE = json.loads((P.OUTPUT_DIR / "d6_baseline_results.json").read_text(encoding="utf-8"))
AP4 = json.loads((P.OUTPUT_DIR / "ap4_d6_results.json").read_text(encoding="utf-8"))
A = RB.ASSETS
LABEL = {"Immobilière": "Real estate", "Automobile": "Automobile", "Equipement": "Equipment + raw materials"}
# Validated categorical slots 1-3 (dataviz reference palette, light mode); ink colours for text and non-entity marks.
COLOR = {"Immobilière": "#2a78d6", "Automobile": "#eb6834", "Equipement": "#1baf7a"}
INK, INK2, MUTED, GRID = "#1f1f1e", "#55544f", "#8a8983", "#e4e3df"
RF = AP4["settings"]["rf_base"]

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"], "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "text.color": INK,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03, "pdf.fonttype": 42,
})


def save(fig, name):
    for ext, kw in (("pdf", {}), ("png", {"dpi": 300})):
        fig.savefig(FIG / f"{name}.{ext}", **kw)
    plt.close(fig)
    print("wrote", name)


def main():
    FIG.mkdir(exist_ok=True)
    m = RB.load_murabaha()  # corrected, Equip + Raw merged
    flags = m["flag"].eq("estimated") if "flag" in m else pd.Series(False, index=m.index)
    merged, R, _ = RB.build()
    R = R.iloc[1:]  # D6: the 77 real returns

    # 1. Historical evolution (log scale: the segments differ by two orders of magnitude)
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    for a in A:
        s = m[a] / 1e3
        ax.plot(s.index, s, color=COLOR[a], lw=1.6, label=LABEL[a])
        ax.plot(s.index[flags], s[flags], ls="none", marker="o", ms=5, mfc="white", mec=COLOR[a], mew=1.2)
    ax.set_yscale("log")
    ax.set_ylabel("Outstanding balance (million MAD, log scale)")
    ax.axvline(pd.Timestamp("2024-09-01"), color=MUTED, lw=0.8, ls="--")
    ax.text(pd.Timestamp("2024-08-01"), ax.get_ylim()[0] * 1.15, "Raw materials reported\nseparately from Sep 2024",
            ha="right", va="bottom", fontsize=7, color=INK2)
    ax.plot([], [], ls="none", marker="o", ms=5, mfc="white", mec=INK2, label="Estimated month (Nov 2019, May 2020)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=7.5)
    save(fig, "historical_evolution")

    # 2. Composition (100% stacked area)
    shares = m[A].div(m[A].sum(1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    ax.stackplot(shares.index, *(shares[a] for a in A), colors=[COLOR[a] for a in A], labels=[LABEL[a] for a in A],
                 edgecolor="white", linewidth=0.8)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of Murabaha financing (%)")
    ax.margins(x=0)
    ax.grid(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=7.5)
    save(fig, "market_share")

    # 3. Correlation heatmap (diverging: orange - neutral grey - blue)
    corr = R[A].corr().values
    cmap = LinearSegmentedColormap.from_list("div", ["#eb6834", "#ecebe7", "#2a78d6"])
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    im = ax.imshow(corr, cmap=cmap, vmin=-1, vmax=1)
    ax.grid(False)
    short = ["Real estate", "Automobile", "Equip. + raw"]
    ax.set_xticks(range(3), short)
    ax.set_yticks(range(3), short)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=9, color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7)
    ax.set_title("Monthly log-growth clipped at ±10%, Aug 2019 – Dec 2025 (n = 77)", fontsize=8, color=INK2)
    save(fig, "correlation_heatmap")

    # 4. Risk-growth profiles of segments and portfolios
    mu = BASE["expected_returns"]
    cov = np.array(BASE["cov_annual"])
    sig = dict(zip(A, np.sqrt(np.diag(cov))))
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for a in A:
        ax.scatter(sig[a] * 100, mu[a] * 100, s=70, color=COLOR[a], edgecolor="white", lw=1.5, zorder=3)
        ax.annotate(LABEL[a], (sig[a] * 100, mu[a] * 100), xytext=(6, -3), textcoords="offset points", fontsize=7.5)
    marks = {"max-Sharpe (baseline)": ("*", 150), "minimum variance": ("s", 40), "equal weight": ("^", 45),
             "risk parity (ERC, bounded)": ("D", 35), "actual book Dec 2025": ("P", 55)}
    names = {"max-Sharpe (baseline)": "Max-Sharpe", "minimum variance": "Min. variance", "equal weight": "Equal weight",
             "risk parity (ERC, bounded)": "Risk parity", "actual book Dec 2025": "Actual mix, Dec 2025"}
    for k, (mk, sz) in marks.items():
        d = AP4["benchmarks_in_sample"][k]
        ax.scatter(d["volatility"] * 100, d["return"] * 100, marker=mk, s=sz, color=INK, zorder=4, label=names[k])
    ax.set_xlabel("Annualized volatility of balance growth (%)")
    ax.set_ylabel("Annualized balance growth (%)")
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, "risk_return_profiles")

    # 5. Optimal weights with bootstrap 90% intervals vs the observed mix
    bw = AP4["bootstrap"]["weights_percentiles"]
    opt = BASE["optimal"]["weights"]
    last = merged[A].iloc[-1] / merged[A].iloc[-1].sum()
    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    for i, a in enumerate(A[::-1]):
        ax.hlines(i, bw[a]["p5"] * 100, bw[a]["p95"] * 100, color=COLOR[a], lw=2.5, alpha=0.45)
        ax.scatter(opt[a] * 100, i, s=60, color=COLOR[a], edgecolor="white", lw=1.5, zorder=3)
        ax.scatter(last[a] * 100, i, s=45, marker="D", facecolor="white", edgecolor=INK, lw=1.2, zorder=3)
        ax.annotate(f"{opt[a]*100:.1f}%", (opt[a] * 100, i), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=7.5)
    ax.set_yticks(range(3), [LABEL[a] for a in A[::-1]])
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, 2.6)
    ax.set_xlabel("Portfolio weight (%)")
    ax.axvline(70, color=MUTED, lw=0.8, ls=":")
    ax.text(70.8, 2.45, "70% cap", fontsize=7, color=INK2)
    ax.grid(axis="y", visible=False)
    h = [plt.Line2D([], [], ls="none", marker="o", ms=7, color=INK2),
         plt.Line2D([], [], color=INK2, lw=2.5, alpha=0.45),
         plt.Line2D([], [], ls="none", marker="D", ms=6, mfc="white", mec=INK)]
    ax.legend(h, ["Optimal (baseline)", "Bootstrap 90% interval", "Actual mix, Dec 2025"], loc="upper center",
              bbox_to_anchor=(0.5, -0.28), ncol=3, fontsize=7.5)
    save(fig, "strategic_allocation")

    # 6. Constrained QP frontier, Monte Carlo feasible set, tangency and capital allocation line
    pts = AP4["qp_frontier"]["points"]
    cloud, _ = P.simulate_efficient_frontier(pd.Series(mu)[A], pd.DataFrame(cov, A, A), RF)
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    ax.scatter(cloud["volatility"] * 100, cloud["return"] * 100, s=2, color="#c9c8c2", lw=0, zorder=1,
               label="Feasible portfolios (Monte Carlo, n = 8,000)")
    ax.plot([p["volatility"] * 100 for p in pts], [p["target"] * 100 for p in pts], color=INK, lw=1.8, zorder=2,
            label="Constrained efficient frontier (QP)")
    b = BASE["optimal"]
    x = np.linspace(0, max(p["volatility"] for p in pts) * 100, 50)
    ax.plot(x, RF * 100 + b["sharpe"] * x, color=INK2, lw=0.9, ls="--", zorder=2, label=f"Line from Rf = {RF*100:.1f}%")
    ax.scatter(b["volatility"] * 100, b["return"] * 100, marker="*", s=180, color=INK, edgecolor="white", lw=0.8,
               zorder=5, label=f"Max-Sharpe (growth SR = {b['sharpe']:.2f})")
    for a in A:
        ax.scatter(sig[a] * 100, mu[a] * 100, s=55, color=COLOR[a], edgecolor="white", lw=1.5, zorder=4)
        below = a == "Immobilière"  # keep the label off the Monte Carlo cloud and the Rf line
        ax.annotate(LABEL[a], (sig[a] * 100, mu[a] * 100), xytext=(0, -13) if below else (6, -3),
                    textcoords="offset points", fontsize=7.5, ha="center" if below else "left")
    ax.set_xlim(0, max(sig.values()) * 100 * 1.25)
    ax.set_ylim(0, max(mu.values()) * 100 * 1.1)
    ax.set_xlabel("Annualized volatility of balance growth (%)")
    ax.set_ylabel("Annualized balance growth (%)")
    ax.legend(loc="lower right", fontsize=7.5)
    save(fig, "efficient_frontier")


if __name__ == "__main__":
    main()
