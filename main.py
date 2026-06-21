# main.py
import asyncio
import json
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
from models import PromptData
from orchestrator import run_single_mode, run_isolated_mode, run_hybrid_mode
from logger import save_results, load_ground_truth

console = Console()

async def main():
    console.print("[bold blue]🚀 Starting Variety Deficit Scan v2.0...[/bold blue]")
    
    # Load Dataset
    try:
        with open('prompts.json', 'r') as f:
            data = json.load(f)
        prompts = [PromptData(**p) for p in data['prompts']]
    except FileNotFoundError:
        console.print("[red]❌ prompts.json not found.[/red]")
        return
    except Exception as e:
        console.print(f"[red]❌ Error loading prompts: {e}[/red]")
        return

    # Load Ground Truth for accuracy scoring
    expected_map = load_ground_truth('prompts.json')
    if expected_map:
        console.print(f"[green]✅ Loaded ground truth for {len(expected_map)} prompts.[/green]")
    else:
        console.print("[yellow]⚠️ No ground truth found. Accuracy scoring will be skipped.[/yellow]")

    total_tasks = len(prompts) * 3
    results = []
    error_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Running Batch...", total=total_tasks)
        
        for i, p in enumerate(prompts):
            prompt_id = p.id
            prompt_text = p.text
            
            # Run all 3 modes concurrently
            tasks = [
                run_single_mode(prompt_id, prompt_text),
                run_isolated_mode(prompt_id, prompt_text),
                run_hybrid_mode(prompt_id, prompt_text)
            ]
            
            try:
                mode_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for j, res in enumerate(mode_results):
                    mode_name = ["single_call", "isolated_call", "hybrid_call"][j]
                    
                    if isinstance(res, Exception):
                        console.print(f"[yellow]⚠️ Error in {mode_name}: {res}[/yellow]")
                        error_count += 1
                        result_data = {
                            "prompt_id": prompt_id,
                            "category": p.category,
                            "prompt_text": prompt_text,
                            "mode": mode_name,
                            "l1_output": "",
                            "l2_decision": "ERROR",
                            "l2_confidence": 0,
                            "l2_reason": str(res),
                            "final_output": "",
                            "latency_ms": 0
                        }
                    else:
                        result_data = {
                            "prompt_id": prompt_id,
                            "category": p.category,
                            "prompt_text": prompt_text,
                            **res
                        }
                        
                        decision = result_data.get("l2_decision", "N/A")
                        conf = result_data.get("l2_confidence", "N/A")
                        console.print(f"   [{i+1}/{len(prompts)}] Mode: {mode_name:12} | Dec: {decision:5} | Conf: {conf}%")
                    
                    results.append(result_data)
                    progress.advance(task)
            
            except Exception as e:
                console.print(f"[red]Fatal error processing prompt {prompt_id}: {e}[/red]")
                error_count += 1

    console.print(f"\n[bold]Batch Complete![/bold]")
    console.print(f"Total Runs: {len(results)}, Errors: {error_count}")
    
    # Save with accuracy scoring
    filename, accuracy_results = save_results(results, expected_map=expected_map)


if __name__ == "__main__":
    asyncio.run(main())