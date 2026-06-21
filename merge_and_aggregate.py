#!/usr/bin/env python3
"""
Merge ALL repeat-run CSVs and compute aggregate block rates per prompt/mode.
This gives you ONE trustworthy number per prompt instead of conflicting snapshots.
BUG-FIXED VERSION: Handles missing columns, inconsistent naming, and empty files.
"""

import pandas as pd
import glob
import sys
from rich.console import Console
from rich.table import Table

console = Console()

# ── Configuration ─────────────────────────────────────────────────────────────
MIN_RUNS_REQUIRED = 2  # Minimum runs before we trust a result
DECISION_KEYWORDS = {"BLOCK", "BLOCKED", "ERROR"}

def normalize_decision(decision):
    """Convert various decision formats to standard BLOCK/ALLOW."""
    if pd.isna(decision):
        return "UNKNOWN"
    decision = str(decision).strip().upper()
    for keyword in DECISION_KEYWORDS:
        if keyword in decision:
            return "BLOCK"
    return "ALLOW"

def extract_prompt_id(run_id):
    """Extract base prompt ID from run IDs like 'TRAP_01_r0'."""
    if pd.isna(run_id):
        return "UNKNOWN"
    run_id = str(run_id)
    # Remove _r0, _r1, _r2 suffixes
    import re
    match = re.match(r"^([A-Z\d_]+)_?\d*$", run_id)
    if match:
        return match.group(1)
    return run_id.replace("_r0", "").replace("_r1", "").replace("_r2", "")

# ── Load All CSVs ────────────────────────────────────────────────────────────
csv_files = sorted(glob.glob("results/*.csv"))

if len(csv_files) == 0:
    console.print("[red]❌ No CSV files found in results/ folder![/red]")
    sys.exit(1)

console.print(f"[bold]Found {len(csv_files)} CSV file(s):[/bold]")
for f in csv_files[:10]:  # Show first 10
    console.print(f"  • {f}")
if len(csv_files) > 10:
    console.print(f"  ... and {len(csv_files)-10} more")

dfs = []
skipped = 0

for filepath in csv_files:
    try:
        df = pd.read_csv(filepath)
        
        # Skip completely empty files
        if df.empty:
            console.print(f"[yellow]⚠️ Skipping {filepath}: Empty file[/yellow]")
            skipped += 1
            continue
        
        # Check for required columns
        if "mode" not in df.columns:
            console.print(f"[yellow]⚠️ Skipping {filepath}: No 'mode' column[/yellow]")
            skipped += 1
            continue
        
        # Add original filename for tracking
        df["_source_file"] = filepath.split("/")[-1]
        
        # Extract prompt ID if needed
        if "run_id" in df.columns and "prompt_id" not in df.columns:
            df["original_id"] = df["run_id"].apply(extract_prompt_id)
        
        dfs.append(df)
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Skipping {filepath}: {str(e)[:50]}[/yellow]")
        skipped += 1

if len(dfs) == 0:
    console.print("[red]❌ No valid CSV files to process![/red]")
    sys.exit(1)

merged = pd.concat(dfs, ignore_index=True)
console.print(f"\n[bold green]Merged: {len(merged)} total rows from {len(dfs)} files ({skipped} skipped)[/bold green]")

# ── Normalize Data ───────────────────────────────────────────────────────────
# Determine the correct prompt ID column
id_col = None
if "original_id" in merged.columns:
    id_col = "original_id"
elif "prompt_id" in merged.columns:
    id_col = "prompt_id"
else:
    console.print("[red]❌ Cannot find prompt ID column![/red]")
    sys.exit(1)

# Clean and normalize mode column
merged["mode"] = merged["mode"].astype(str).str.strip().str.lower()
valid_modes = ["isolated_call", "isolated", "hybrid_call", "hybrid"]

# Map variants to canonical names
mode_mapping = {
    "isolated": "isolated_call",
    "hybrid": "hybrid_call",
    "isolated_call": "isolated_call",
    "hybrid_call": "hybrid_call"
}
merged["mode"] = merged["mode"].map(lambda x: mode_mapping.get(x, x))

# Filter to isolated/hybrid only
merged = merged[merged["mode"].isin(["isolated_call", "hybrid_call"])]

if len(merged) == 0:
    console.print("[red]❌ No isolated/hybrid data after filtering![/red]")
    sys.exit(1)

# Normalize decisions
merged["l2_decision_normalized"] = merged["l2_decision"].apply(normalize_decision)

# ── Aggregate Stats ───────────────────────────────────────────────────────────
table = Table(show_header=True, header_style="bold")
table.add_column("Prompt ID")
table.add_column("Total Runs", justify="center")
table.add_column("Iso Block %", justify="right")
table.add_column("Hyb Block %", justify="right")
table.add_column("Divergence", justify="center")
table.add_column("Confidence", justify="center")

results = []

for pid in sorted(merged[id_col].unique()):
    pid_rows = merged[merged[id_col] == pid]
    
    iso_rows = pid_rows[pid_rows["mode"] == "isolated_call"]
    hyb_rows = pid_rows[pid_rows["mode"] == "hybrid_call"]
    
    iso_total = len(iso_rows)
    hyb_total = len(hyb_rows)
    
    # Only calculate if we have data
    if iso_total > 0:
        iso_blocks = sum(1 for _, r in iso_rows.iterrows() if r["l2_decision_normalized"] == "BLOCK")
        iso_pct = round(iso_blocks / iso_total * 100, 1)
    else:
        iso_pct = None
    
    if hyb_total > 0:
        hyb_blocks = sum(1 for _, r in hyb_rows.iterrows() if r["l2_decision_normalized"] == "BLOCK")
        hyb_pct = round(hyb_blocks / hyb_total * 100, 1)
    else:
        hyb_pct = None
    
    # Calculate divergence
    if iso_pct is not None and hyb_pct is not None:
        diff = abs(iso_pct - hyb_pct)
        if diff >= 50:
            div = "STRONG"
            conf = "HIGH"
        elif diff >= 20:
            div = "Partial"
            conf = "MEDIUM"
        elif diff > 0:
            div = "Weak"
            conf = "LOW"
        else:
            div = "None"
            conf = "N/A"
    else:
        div = "-"
        conf = "-"
        diff = 0
    
    total_runs = iso_total + hyb_total
    
    # Display
    table.add_row(
        pid, 
        str(total_runs),
        f"{iso_pct}%" if iso_pct is not None else "-",
        f"{hyb_pct}%" if hyb_pct is not None else "-",
        div,
        conf
    )
    
    results.append({
        "prompt_id": pid,
        "total_runs": total_runs,
        "iso_runs": iso_total,
        "hyb_runs": hyb_total,
        "iso_block_pct": iso_pct,
        "hyb_block_pct": hyb_pct,
        "divergence": div,
        "confidence": conf,
        "diff_pp": diff if diff else 0
    })

console.print(table)

# ── Save Results ─────────────────────────────────────────────────────────────
agg_df = pd.DataFrame(results)
agg_filename = "results/aggregated_all_runs.csv"
agg_df.to_csv(agg_filename, index=False)
console.print(f"\n[green]✅ Aggregated results saved to {agg_filename}[/green]")

# ── Summary Statistics ───────────────────────────────────────────────────────
strong_div = sum(1 for r in results if r["divergence"] == "STRONG")
partial_div = sum(1 for r in results if r["divergence"] == "Partial")
weak_no_div = sum(1 for r in results if r["divergence"] in ["Weak", "None"])
low_confidence = sum(1 for r in results if r["confidence"] in ["LOW", "-"])
high_confidence = sum(1 for r in results if r["confidence"] == "HIGH")

console.print(f"\n[bold]Summary:[/bold]")
console.print(f"  Strong Divergence (≥50pp gap): {strong_div}/{len(results)} prompts")
console.print(f"  Partial Divergence (20-50pp):  {partial_div}/{len(results)} prompts")
console.print(f"  Weak/No Divergence (<20pp):    {weak_no_div}/{len(results)} prompts")
console.print(f"  High Confidence:               {high_confidence}/{len(results)} prompts")
console.print(f"  Low/Unknown Confidence:        {low_confidence}/{len(results)} prompts")

# ── Highlight Key Findings ───────────────────────────────────────────────────
console.print(f"\n[bold cyan]Key Findings for Paper:[/bold cyan]")
for r in results:
    if r["confidence"] == "HIGH" and r["diff_pp"] > 0:
        direction = "Hybrid wins" if r["hyb_block_pct"] > r["iso_block_pct"] else "Isolated wins"
        console.print(f"  • {r['prompt_id']}: {r['iso_block_pct']}% Iso / {r['hyb_block_pct']}% Hyb ({direction})")