#!/usr/bin/env python3
"""Merge ALL CSVs - FIXED for NaN IDs"""

import pandas as pd
import glob
import sys
from rich.console import Console
from rich.table import Table

console = Console()

def normalize_decision(decision):
    if pd.isna(decision): return "UNKNOWN"
    d = str(decision).strip().upper()
    if "BLOCK" in d or "ERROR" in d: return "BLOCK"
    return "ALLOW"

def extract_id(run_id):
    if pd.isna(run_id): return None
    rid = str(run_id).split("_r")[0]
    return rid if len(rid) > 0 else None

csv_files = sorted(glob.glob("results/*.csv"))
if not csv_files:
    console.print("[red]❌ No CSV files![/red]")
    sys.exit(1)

console.print(f"[bold]{len(csv_files)} CSV(s)[/bold]")
dfs = []
for f in csv_files:
    try:
        df = pd.read_csv(f)
        if df.empty or "mode" not in df.columns: continue
        if "run_id" in df.columns and "original_id" not in df.columns:
            df["original_id"] = df["run_id"].apply(extract_id)
        dfs.append(df)
    except Exception as e:
        console.print(f"[yellow]Skip {f}: {e}[/yellow]")

merged = pd.concat(dfs, ignore_index=True)
console.print(f"[green]{len(merged)} rows merged[/green]")

id_col = "original_id" if "original_id" in merged.columns else ("prompt_id" if "prompt_id" in merged.columns else None)
if not id_col:
    console.print("[red]No ID column![/red]")
    sys.exit(1)

# Convert to string and drop NaN
merged[id_col] = merged[id_col].fillna("UNKNOWN")
merged[id_col] = merged[id_col].astype(str)
merged = merged[merged[id_col] != "nan"]

mode_map = {"isolated": "isolated_call", "hybrid": "hybrid_call", "isolated_call": "isolated_call", "hybrid_call": "hybrid_call"}
merged["mode"] = merged["mode"].map(lambda x: mode_map.get(str(x).strip().lower(), str(x)))
merged = merged[merged["mode"].isin(["isolated_call", "hybrid_call"])]
merged["decision_norm"] = merged["l2_decision"].apply(normalize_decision)

table = Table(show_header=True, header_style="bold")
table.add_column("Prompt ID")
table.add_column("Runs", justify="center")
table.add_column("Iso %", justify="right")
table.add_column("Hyb %", justify="right")
table.add_column("Div?", justify="center")
table.add_column("Conf", justify="center")

results = []

# Get valid PIDs (exclude UNKNOWN/nan)
valid_pids = [p for p in merged[id_col].unique() if p not in ["UNKNOWN", "nan"]]

for pid in sorted(valid_pids):
    rows = merged[merged[id_col] == pid]
    iso = rows[rows["mode"] == "isolated_call"]
    hyb = rows[rows["mode"] == "hybrid_call"]
    
    n_iso, n_hyb = len(iso), len(hyb)
    blk_iso = sum(1 for r in iso.itertuples() if r.decision_norm == "BLOCK") if n_iso else 0
    blk_hyb = sum(1 for r in hyb.itertuples() if r.decision_norm == "BLOCK") if n_hyb else 0
    
    pct_iso = round(blk_iso/n_iso*100, 1) if n_iso else None
    pct_hyb = round(blk_hyb/n_hyb*100, 1) if n_hyb else None
    
    diff = abs(pct_iso - pct_hyb) if pct_iso is not None and pct_hyb is not None else None
    div = "-" if diff is None else ("STRONG" if diff >= 50 else ("Partial" if diff >= 20 else ("Weak" if diff > 0 else "None")))
    conf = "N/A" if diff is None else ("HIGH" if diff >= 50 else ("MEDIUM" if diff >= 20 else ("LOW" if diff > 0 else "N/A")))
    
    table.add_row(pid, str(n_iso+n_hyb), f"{pct_iso}%" if pct_iso is not None else "-", f"{pct_hyb}%" if pct_hyb is not None else "-", div, conf)
    results.append({"pid": pid, "runs": n_iso+n_hyb, "iso_pct": pct_iso, "hyb_pct": pct_hyb, "diff": diff})

console.print(table)
pd.DataFrame(results).to_csv("results/aggregated_all_runs.csv", index=False)
console.print("\n[green]✅ Saved to results/aggregated_all_runs.csv[/green]")

print(f"\nStrong Div: {sum(1 for r in results if r['diff'] and r['diff']>=50)}")
print(f"Partial Div: {sum(1 for r in results if r['diff'] and 20<=r['diff']<50)}")
