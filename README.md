# Murabaha portfolio allocation: replication package

Data and code for the paper **"Quadratic Programming for Murabaha Portfolio Risk Management: A Strategic Asset Allocation Framework"** by Soukaina Hlal, Asmae Daaou, Abdelwadoud El Khalfi, Mohamed El Gharb, Asmaa Faris and Mostafa El Hachloufi (Hassan II University, Casablanca). The manuscript is under revision at *Statistics, Optimization & Information Computing* (SOIC).

The package rebuilds every number, table and figure in the paper from the raw data with one command.

A one-page summary of the study is at https://kh-abdo.github.io/murabaha-portfolio-replication/ (source: `docs/index.html`).

## Quick start

Python 3.12 was used.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run_all.py
```

The run takes about four minutes on a laptop, mostly for the bootstrap. It overwrites `data/data_corrected.xlsx`, `outputs/`, `figures/` and `tables/`. The committed copies of these files are the ones used in the paper, so `git status` after a run shows any difference. A clean rerun reproduces `outputs/`, `tables/` and the PNG figures byte for byte. Only the `.xlsx` and PDF files show as modified, because they embed a creation timestamp.

## What is in the package

| Path | Contents |
|---|---|
| `data/raw/data.xlsx` | Month-end outstanding Murabaha financing by sector (thousand MAD), transcribed by hand from Bank Al-Maghrib's monthly reports *Indicateurs des banques et fenêtres participatives*. |
| `data/raw/4CPBFP.xlsx` | Bank Al-Maghrib balance-sheet statistics for participatory banks (sheet `CP_BANUQ_PAR`). Used only for the investment-deposit series reported alongside the assumed reference rate. |
| `data/data_corrected.xlsx` | The corrected dataset used in the paper. Sheet `corrections_log` lists every change with its source. |
| `code/` | The analysis scripts (below). |
| `outputs/` | Result files (JSON and plain-text reports). |
| `figures/` | Figures as vector PDF and 300 dpi PNG. |
| `tables/` | LaTeX tables and `results_macros.tex`; the manuscript inputs these, so no reported number is typed by hand. |

## Pipeline

`run_all.py` runs these steps in order, each from inside `code/`:

| Step | Script | Produces |
|---|---|---|
| 1 | `build_corrected_data.py` | `data/data_corrected.xlsx` from `data/raw/data.xlsx` |
| 2 | `pipeline.py --merge-raw --drop-first-zero --tag d6_baseline` | Baseline: three segments (equipment includes raw materials), 77 monthly changes |
| 3 | `pipeline.py --drop-first-zero --tag d6_separate` | Four-segment variant (raw materials separate), Appendix B |
| 4 | `robustness.py` | Sensitivity grids, bootstrap and out-of-sample tests (`outputs/ap4_d6_*`) |
| 5 | `ap4_tables.py` | Markdown view of the robustness results |
| 6 | `make_figures.py` | `figures/` |
| 7 | `make_tex_tables.py` | `tables/` |

## Data corrections

The raw workbook was checked cell by cell against the Bank Al-Maghrib reports. `build_corrected_data.py` applies these corrections; its header and the `corrections_log` sheet document each one.

- **October 2020, real estate:** the cell had copied the total.
- **December 2022, equipment:** the cell had copied the automobile value.
- **November 2019 and May 2020:** no report was available. Values are reconstructed from the next report's published monthly variation, with bounds in sheet `estimate_bounds`.
- **September 2024:** Bank Al-Maghrib reclassified raw-materials financing out of equipment. The baseline adds the two back together so the series is consistent over the whole sample.

## How to read the results

The published data are outstanding balances. The model therefore uses the monthly log-growth of balances as a proxy for each segment's performance. **Balance growth is not an investment return or a profit rate**, and the "growth-to-volatility ratio" is a Sharpe-type ratio of growth, not a Sharpe ratio of returns. The 4.5% reference rate, the 70% real-estate ceiling and the 2% floors are assumptions of the authors, not regulatory or Sharia rules. The paper's Limitations section explains this in full.

## Software

Tested with Python 3.12.10 on Windows, with the versions pinned in `requirements.txt`. The optimizer is SciPy's SLSQP.
