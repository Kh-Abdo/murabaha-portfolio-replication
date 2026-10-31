"""Rebuild every result, figure and table of the paper from the raw data, in order.

Usage (from the package root):  python run_all.py
"""
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent / "code"
STEPS = [
    ["build_corrected_data.py"],
    ["pipeline.py", "--data", "../data/data_corrected.xlsx", "--merge-raw", "--drop-first-zero", "--tag", "d6_baseline"],
    ["pipeline.py", "--data", "../data/data_corrected.xlsx", "--drop-first-zero", "--tag", "d6_separate"],
    ["robustness.py"],
    ["ap4_tables.py"],
    ["make_figures.py"],
    ["make_tex_tables.py"],
]

for step in STEPS:
    print(">>", " ".join(step), flush=True)
    subprocess.run([sys.executable, "-P", *step], cwd=CODE, check=True)
print("Done. See outputs/, figures/ and tables/.")
