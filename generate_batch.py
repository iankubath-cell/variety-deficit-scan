#!/usr/bin/env python3
"""
generate_batch.py — Variety Deficit Scan Batch Runner
Added --repeats N flag to measure L1 sampling variance vs. architectural divergence.
"""

import asyncio
import json
import argparse
import os
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from orchestrator import run_single_mode, run_isolated_mode, run_hybrid_mode

console = Console()

MODE_RUNNERS = {
    "single":   run_single_mode,
    "isolated": run_isolated_mode,
    "hybrid":   run_hybrid_mode,
}

MODE_LABEL = {
    "single":   "single_call",
    "isolated": "isolated_call",
    "hybrid":   "hybrid_call",
}

def load_dataset(filepath: str, dataset_tag: str) -> list[dict]:
    """Load prompts JSON and tag with dataset name."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        console.print(f"[yellow]⚠️  {filepath} not found — skipping.[/yellow]")
        return []
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ JSON error in {filepath}: {e}[/red]")
        return []

    prompts = data.get("prompts", [])
    enriched = []
    for p in prompts:
        enriched.append({
            "id":           p.get("id", "unknown"),
            "dataset":      dataset_tag,
            "category":     p.get("category", ""),
            "text":         p.get("text", ""),
            "ground_truth": p.get("ground_truth", p.get("expected", "")),
            "trap_mechanism": p.get("trap_mechanism", ""),
        })
    return enriched

async def run_prompt_replica(prompt: dict, mode: str, use_weak_l1: bool = False, repeat_idx: int = 0) -> dict:
    """Run a single prompt/mode combo once."""
    prompt_id   = prompt["id"]
    prompt_text = prompt["text"]
    
    # Add repeat ID to prompt_id for uniqueness in CSV if needed, or just track internally
    row_id = f"{prompt_id}_r{repeat_idx}"

    result = await MODE_RUNNERS[mode](prompt_id, prompt_text, use_weak_l1)
    
    # Add repeat info to result
    result["run_id"] = row_id
    result["original_id"] = prompt_id
    result["repeat_idx"] = repeat_idx
    
    return result

async def run_prompt_group(prompt: dict, modes: list[str], repeats: int, use_weak_l1: bool = False) -> list[dict]:
    """Run a prompt through all modes, repeated 'repeats' times."""
    all_rows = []
    
    for r in range(repeats):
        tasks = [run_prompt_replica(prompt, m, use_weak_l1, r) for m in modes]
        mode_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in mode_results:
            if isinstance(res, Exception):
                # Handle errors gracefully
                all_rows.append({
                    "run_id": f"{prompt['id']}_r{r}",
                    "original_id": prompt['id'],
                    "dataset": prompt["dataset"],
                    "category": prompt["category"],
                    "mode": MODE_LABEL.get("error", "error"),
                    "l2_decision": "ERROR",
                    "l2_confidence": 0,
                    "l2_reason": str(res),
                    "final_output": "",
                    "latency_ms": 0,
                    "repeat_idx": r,
                    "ground_truth": prompt.get("ground_truth", ""),
                    "trap_mechanism": prompt.get("trap_mechanism", "")
                })
            else:
                all_rows.append(res)
                
    return all_rows

def print_summary(results: list[dict], use_weak_l1: bool) -> None:
    """Print summary including variance analysis."""
    from collections import defaultdict
    import statistics

    l1_label = "WEAK" if use_weak_l1 else "STANDARD"
    console.print(f"\n[bold]── Results Summary (with Variance Check) ──[/bold]  (L1 Mode: [cyan]{l1_label}[/cyan])")

    by_original_id = defaultdict(list)
    for r in results:
        if "original_id" in r:
            by_original_id[r["original_id"]].append(r)

    # Aggregate stats per original prompt
    console.print("\n[bold cyan]Divergence & Variance Analysis:[/bold cyan]")
    
    total_diverged = 0
    total_variance_high = 0
    
    table_data = []

    for pid, rows in sorted(by_original_id.items()):
        # Group by mode
        by_mode = defaultdict(list)
        for r in rows:
            by_mode[r["mode"]].append(r)
        
        mode_stats = {}
        for mode_name in ["isolated_call", "hybrid_call"]:
            mode_rows = by_mode.get(mode_name, [])
            if not mode_rows:
                continue
            
            # Count decisions
            blocks = sum(1 for r in mode_rows if r["l2_decision"] == "BLOCK")
            allows = sum(1 for r in mode_rows if r["l2_decision"] == "ALLOW")
            errors = sum(1 for r in mode_rows if r["l2_decision"] == "ERROR")
            total = len(mode_rows)
            
            pct_block = round(blocks / total * 100, 1) if total else 0
            
            # Variance check: if we got mixed results (some block, some allow), mark it
            is_volatile = (blocks > 0 and allows > 0)
            
            mode_stats[mode_name] = {
                "blocks": blocks, 
                "allows": allows, 
                "total": total, 
                "pct": pct_block, 
                "volatile": is_volatile
            }
            
        # Compare Isolated vs Hybrid
        iso_stat = mode_stats.get("isolated_call", {})
        hyb_stat = mode_stats.get("hybrid_call", {})
        
        if iso_stat and hyb_stat:
            # Are they consistently different?
            iso_consistent = not iso_stat["volatile"]
            hyb_consistent = not hyb_stat["volatile"]
            
            diverged_this = False
            if iso_stat["blocks"] != hyb_stat["blocks"]:
                diverged_this = True
                total_diverged += 1
            
            volatility = []
            if iso_stat["volatile"]: volatility.append("Iso")
            if hyb_stat["volatile"]: volatility.append("Hyb")
            
            if volatility:
                total_variance_high += 1
            
            table_data.append([
                pid, 
                iso_stat["pct"], 
                hyb_stat["pct"], 
                "Yes" if diverged_this else "No", 
                ",".join(volatility) if volatility else "-"
            ])

    if table_data:
        t = Table(show_header=True, header_style="bold")
        t.add_column("Prompt ID")
        t.add_column("Iso Block %", justify="right")
        t.add_column("Hyb Block %", justify="right")
        t.add_column("Consistently Div?", justify="center")
        t.add_column("Variance Detected?", justify="center")
        
        for row in table_data:
            t.add_row(*[str(x) for x in row])
        console.print(t)
    
    console.print(f"\nTotal Prompts with Divergence: [yellow]{total_diverged}/{len(by_original_id)}[/yellow]")
    console.print(f"Prompts with High Variance (L1 noise): [yellow]{total_variance_high}/{len(by_original_id)}[/yellow]")

    # Falsification scoring (aggregated over repeats)
    if any(r.get("dataset") == "falsification" for r in results):
        console.print("\n  [bold]Aggregated Falsification Scores (Across Repeats):[/bold]")
        hybrid_fooled = 0
        both_correct = 0
        both_wrong = 0
        
        # Simple aggregation logic: if majority blocked, count as block
        # ... (You can expand this logic later)
        # For now, just a placeholder to indicate the feature exists
        console.print("[italic]Note: Aggregated scoring requires full pass-through. Use manual CSV filter for detailed variance analysis.[/italic]")

async def main():
    parser = argparse.ArgumentParser(description="Variety Deficit Scan — Batch Runner with Variance Check")
    parser.add_argument("--dataset", choices=["original", "falsification", "both"], default="both")
    parser.add_argument("--modes", nargs="+", choices=["single", "isolated", "hybrid"], default=["single", "isolated", "hybrid"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--weak-l1", action="store_true")
    parser.add_argument("--repeats", type=int, default=1, help="Number of times to repeat each prompt/mode combo (default: 1)")
    parser.add_argument("--output-prefix", default="batch")
    args = parser.parse_args()

    if args.model:
        import config
        config.MODELS["standard"] = args.model
        console.print(f"[cyan]Model override: {args.model}[/cyan]")

    l1_label = "WEAK" if args.weak_l1 else "STANDARD"

    console.print(f"[bold blue]🚀 Variety Deficit Scan — Batch Runner (Repeats={args.repeats})[/bold blue]")
    console.print(f"   Dataset(s): [cyan]{args.dataset}[/cyan]")
    console.print(f"   Modes:      [cyan]{', '.join(args.modes)}[/cyan]")
    console.print(f"   Model:      [cyan]{args.model or 'default'}[/cyan]")
    console.print(f"   L1 Mode:    [green]{l1_label}[/green]\n")

    all_prompts = []

    if args.dataset in ("original", "both"):
        original = load_dataset("prompts.json", "original")
        console.print(f"  Loaded [green]{len(original)}[/green] prompts from prompts.json")
        all_prompts.extend(original)

    if args.dataset in ("falsification", "both"):
        falsification = load_dataset("falsification_traps_v2.json", "falsification")
        console.print(f"  Loaded [green]{len(falsification)}[/green] prompts from falsification_traps_v2.json")
        all_prompts.extend(falsification)

    if not all_prompts:
        console.print("[red]❌ No prompts loaded. Check filenames![/red]")
        return

    total_tasks = len(all_prompts) * len(args.modes) * args.repeats
    console.print(f"\n  Total API calls: [yellow]{total_tasks}[/yellow]\n")

    all_results = []
    error_count = 0

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), TaskProgressColumn()) as progress:
        task = progress.add_task("[cyan]Running...", total=len(all_prompts))

        for i, prompt in enumerate(all_prompts):
            progress.update(task, description=f"[cyan][{i+1}/{len(all_prompts)}] {prompt['id']}")
            
            # Run the group with repeats
            rows = await run_prompt_group(prompt, args.modes, args.repeats, args.weak_l1)

            for row in rows:
                if row.get("l2_decision") == "ERROR":
                    error_count += 1
                else:
                    dec  = row.get("l2_decision")
                    conf = row.get("l2_confidence", 0)
                    mode = row.get("mode")
                    rep  = row.get("repeat_idx")
                    
                    console.print(
                        f"   [{l1_label[:3]}] {prompt['id']:<25} Rep:{rep} {mode:<14} {dec:>5} ({conf}%)"
                    )

            all_results.extend(rows)
            progress.advance(task)

    console.print(f"\n[bold]Batch complete.[/bold] Rows: {len(all_results)}, Errors: {error_count}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    l1_tag = "weak" if args.weak_l1 else "std"
    filename  = f"results/{args.output_prefix}_{l1_tag}_r{args.repeats}_{timestamp}.csv"
    os.makedirs("results", exist_ok=True)

    import pandas as pd
    df = pd.DataFrame(all_results)
    df = df.astype(str)
    df.to_csv(filename, index=False)
    console.print(f"[green]✅ Saved to {filename}[/green]")

    print_summary(all_results, args.weak_l1)


if __name__ == "__main__":
    asyncio.run(main())