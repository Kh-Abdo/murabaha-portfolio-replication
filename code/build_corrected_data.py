"""AP3: build a corrected working copy of data.xlsx. The original is read only and never modified.

Corrections (all traced to the BKAM monthly reports):
  2020-10 Immobilière   12,293,085 -> 10,978,805  (xlsx had copied the Total)
  2022-12 Equipement     1,411,341 ->  1,782,807  (xlsx had copied Automobile)
  2019-11 all columns    copy of the 2020-11 row -> estimated (no report available)
  2020-05 all columns    blank                   -> estimated (no report available)

Estimation for the two months without a report: back out the month from the next report's
published monthly variation, V_missing = V_next / (1 + g), where g is BAM's rounded whole-percent
change (Dec 2019 report for Nov 2019; Jun 2020 report for May 2020). Bounds use g +/- 0.5 pp.
Alternatives (log-linear interpolation, left missing) are written to a separate sheet.

Writes: data/data_corrected.xlsx
Usage (from this folder):  python -P build_corrected_data.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "data.xlsx"
OUT = ROOT / "data" / "data_corrected.xlsx"

SECTORS = ["Immobilière", "Automobile", "Equipement", "Matieres Premieres"]
SHARES = ["Part Immobiliere %", "Part Automobile %", "Part Equipement %", "Part Matieres Premieres%"]

# Value corrections read from the reports: (month, column, wrong value, report value, report file).
CORRECTIONS = [
    ("2020-10", "Immobilière", 12_293_085, 10_978_805, "TDB Indicateurs des banques participatives-Octobre 2020.pdf"),
    ("2022-12", "Equipement", 1_411_341, 1_782_807,
     "indicateurs de l’activité des banques et fenêtres participatives à fin décembre 2022.pdf"),
]

# Next-month level and BAM's published monthly variation (whole %), for back-estimation.
ESTIMATES = {
    "2019-11": {"source": "TDB banques participatives-Décembre 2019.pdf",
                "Totale": (9_100_933, 0.06), "Immobilière": (8_185_125, 0.06),
                "Automobile": (813_469, 0.08), "Equipement": (102_339, 0.66)},
    "2020-05": {"source": "TDB Indicateurs des banques participatives-Juin 2020.pdf",
                "Totale": (10_661_135, 0.04), "Immobilière": (9_583_102, 0.04),
                "Automobile": (929_303, 0.02), "Equipement": (148_729, 0.12)},
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    raw = pd.read_excel(SRC, sheet_name="Feuil1")
    raw = raw[[c for c in raw.columns if not str(c).startswith("Unnamed")]]
    df = raw.copy()
    df["Date"] = df["Date"].astype(str).str[:7]
    df = df.set_index("Date")
    df["flag"] = ""
    log = []

    for month, col, wrong, right, src in CORRECTIONS:
        assert df.at[month, col] == wrong, (month, col, df.at[month, col])
        df.at[month, col] = right
        df.at[month, "flag"] = "corrected"
        log.append({"Date": month, "column": col, "original": wrong, "corrected": right,
                    "method": "value printed in BKAM report", "source": src})

    bounds = []
    for month, spec in ESTIMATES.items():
        for col in ["Totale", "Immobilière", "Automobile", "Equipement"]:
            nxt, g = spec[col]
            est = nxt / (1 + g)
            lo, hi = nxt / (1 + g + 0.005), nxt / (1 + g - 0.005)
            log.append({"Date": month, "column": col, "original": df.at[month, col], "corrected": round(est),
                        "method": f"next-month level / (1 + {g:.0%}) published monthly variation",
                        "source": spec["source"]})
            bounds.append({"Date": month, "column": col, "estimate": round(est), "low": round(lo), "high": round(hi),
                           "half_width_pct": round(100 * (hi - lo) / 2 / est, 3)})
            df.at[month, col] = round(est)
        df.at[month, "Matieres Premieres"] = 0
        df.at[month, "flag"] = "estimated"

    # Shares recomputed from the corrected levels, as in the source sheet (sector / Totale * 100).
    for s, sh in zip(SECTORS, SHARES):
        df[sh] = df[s] / df["Totale"] * 100

    # Consistency check: Totale vs sum of sectors (rows with no estimate should match exactly).
    df["sum_sectors_minus_total"] = df[SECTORS].sum(axis=1) - df["Totale"]

    # Alternatives for the two gap months (sensitivity only; not used in the main sheet).
    orig = raw.copy()
    orig["Date"] = orig["Date"].astype(str).str[:7]
    orig = orig.set_index("Date")
    alt = df[["Totale", "Immobilière", "Automobile", "Equipement"]].copy()
    alt_log = alt.copy()
    for m in ESTIMATES:
        alt_log.loc[m] = np.nan
    alt_log = np.exp(np.log(alt_log.astype(float)).interpolate(method="linear")).round()
    alternatives = pd.concat({
        "variation_implied (main)": alt.loc[list(ESTIMATES)],
        "log_linear_interpolation": alt_log.loc[list(ESTIMATES)],
    }).reset_index().rename(columns={"level_0": "method"})

    # Reclassification view (decision D3): equipment + raw materials as one asset.
    merged_view = df[["Totale", "Immobilière", "Automobile"]].copy()
    merged_view["Equipement + Matieres Premieres"] = df["Equipement"] + df["Matieres Premieres"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    main_sheet = df.drop(columns=["sum_sectors_minus_total"]).reset_index()
    with pd.ExcelWriter(OUT, engine="openpyxl") as w:
        main_sheet.to_excel(w, sheet_name="Feuil1", index=False)
        pd.DataFrame(log).to_excel(w, sheet_name="corrections_log", index=False)
        pd.DataFrame(bounds).to_excel(w, sheet_name="estimate_bounds", index=False)
        alternatives.to_excel(w, sheet_name="gap_alternatives", index=False)
        merged_view.reset_index().to_excel(w, sheet_name="equip_plus_raw_view", index=False)

    chk = df["sum_sectors_minus_total"]
    print("rows:", len(df), "| corrected:", (df.flag == "corrected").sum(), "| estimated:", (df.flag == "estimated").sum())
    print("total vs sum of sectors, non-estimated rows: max |diff| =",
          chk[df.flag != "estimated"].abs().max())
    print("estimated rows diff:", chk[df.flag == "estimated"].to_dict())
    print("original rows where total != sum:", (orig[SECTORS].sum(axis=1) - orig["Totale"]).loc[lambda s: s.abs() > 0].to_dict())
    print(pd.DataFrame(bounds).to_string(index=False))
    print(alternatives.to_string(index=False))
    print("written:", OUT)


if __name__ == "__main__":
    main()
