# logger.py
import pandas as pd
import os
from datetime import datetime
from rich.console import Console

console = Console()

def save_results(results_list, prefix="scan"):
    if not results_list:
        console.print("[red]⚠️ No results to save.[/red]")
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"results/results_{prefix}_{timestamp}.csv"
    
    os.makedirs("results", exist_ok=True)
    
    try:
        df = pd.DataFrame(results_list)
        # Ensure all columns are strings for safety
        df = df.astype(str) 
        
        df.to_csv(filename, index=False)
        console.print(f"[green]✅ Results saved to[/green] {filename}")
        return filename
    except Exception as e:
        console.print(f"[red]❌ Error saving results: {e}[/red]")
        return None
