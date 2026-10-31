"""Render an AP4 results JSON as Markdown tables, so audit notes and the manuscript copy numbers, not retype them.

Usage (from this folder):  python -P ap4_tables.py [tag]     (default tag ap4_d6)
Reads outputs/<tag>_results.json; writes outputs/<tag>_tables.md.
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "outputs"
tag = sys.argv[1] if len(sys.argv) > 1 else "ap4_d6"
o = json.loads((OUT / f"{tag}_results.json").read_text(encoding="utf-8"))
A = o["settings"]["assets"]
pc = lambda x: f"{x * 100:.2f}"


def row(label, d, extra=()):
    w = d["weights"]
    return "| " + " | ".join([label, *(pc(w[a]) for a in A), pc(d["return"]), pc(d["volatility"]),
                              f"{d['sharpe']:.3f}", *extra]) + " |"


HEAD = "| {} | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR |{}\n|---|---|---|---|---|---|---|{}"
L = [f"# AP4 tables — `{tag}` (generated from `{tag}_results.json`; do not edit by hand)\n",
     f"Settings: `{json.dumps({k: v for k, v in o['settings'].items() if k != 'data'}, ensure_ascii=False)}`\n"]


def table(title, items, first="Case", extra_cols=(), extra=lambda d: ()):
    L.append(f"\n## {title}\n")
    L.append(HEAD.format(first, "".join(f" {c} |" for c in extra_cols), "---|" * len(extra_cols)))
    for k, d in items:
        L.append(row(k, d, extra(d)))


b = o["baseline"]
table("Baseline", [("Baseline", b)], extra_cols=["Binding"], extra=lambda d: [", ".join(d["binding"]) or "none"])
table("Rf grid", o["rf_grid"].items(), "Rf", ["Rf %"], lambda d: [pc(d["rf"])])
table("Cap / floor grid", [(f"cap {d['re_cap']:.2f}, floor {d['floor']:.2f}", d) for d in o["cap_floor_grid"]],
      extra_cols=["Binding"], extra=lambda d: [", ".join(d["binding"]) or "none"])
table("Clip grid", o["clip_grid"].items(), "Clip", ["Equip clipped", "μ Equip %", "Binding"],
      lambda d: [str(d["n_clipped"][A[2]]), pc(d["mu"][A[2]]), ", ".join(d["binding"]) or "none"])
table("Gap-month variants", o["gap_variants"].items())
table("Estimation variants", o["estimation_variants"].items())
table("In-sample benchmarks", o["benchmarks_in_sample"].items(), "Portfolio")

bs = o["bootstrap"]
L.append("\n## Block bootstrap\n\n| Percentile | " + " | ".join(A) + " |\n|---|" + "---|" * len(A))
for p in ["p5", "p25", "p50", "p75", "p95"]:
    L.append(f"| {p} | " + " | ".join(pc(bs["weights_percentiles"][a][p]) for a in A) + " |")
L.append(f"\nResampled mean weights: {bs['weights_mean_resampled']}; RE largest in {bs['share_re_largest_weight']:.1%}; "
         f"RE at 70% cap in {bs['share_re_at_70pct_cap']:.1%}; at 2% floor: {bs['share_at_2pct_floor']}; "
         f"growth SR percentiles {bs['sharpe_in_resample_percentiles']}")

q = o["qp_frontier"]
L.append(f"\n## QP frontier vs MC cloud\n\n{json.dumps({k: v for k, v in q.items() if k != 'points'}, indent=1)}")

oo = o["out_of_sample"]
L.append(f"\n## Out of sample, {oo['first_month'][:7]} to {oo['last_month'][:7]} ({oo['n_months']} months)")
for scheme, res in oo["results"].items():
    L.append(f"\n### {scheme} window\n\n| Strategy | Avg RE / Auto / Eq | Return % | Vol % | Growth SR | Unclipped SR"
             " | Turnover/yr | SR @50bp |\n|---|---|---|---|---|---|---|---|")
    for s, r in res.items():
        c0, u0, w = r["clipped_0bp"], r["unclipped_0bp"], r["avg_weights"]
        L.append(f"| {s} | {' / '.join(f'{w[a]*100:.1f}' for a in A)} | {pc(c0['return'])} | {pc(c0['volatility'])} | "
                 f"{c0['sharpe']:.3f} | {u0['sharpe']:.3f} | {r['annual_turnover_clipped']:.3f} | "
                 f"{r['clipped_50bp']['sharpe']:.3f} |")

tv = o["time_variation"]
L.append("\n## Time variation\n\n| Pair | Min | Median | Max | Last | Full sample |\n|---|---|---|---|---|---|")
for k, d in tv["rolling_24m_correlation"].items():
    L.append(f"| {k} | " + " | ".join(f"{d[x]:.2f}" for x in ["min", "median", "max", "last", "full_sample"]) + " |")
table("Split sample", tv["split_sample"].items(), "Period")

(OUT / f"{tag}_tables.md").write_text("\n".join(L) + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(L))
