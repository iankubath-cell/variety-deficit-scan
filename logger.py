# logger.py
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


def load_ground_truth(filepath: str) -> Dict[str, str]:
    """Load ground-truth expected values from prompts.json."""
    import json
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Build dict: {prompt_id: expected_decision}
        expected_map = {}
        for prompt in data['prompts']:
            pid = prompt.get('id', '')
            exp = prompt.get('expected', 'UNKNOWN')
            if pid:
                expected_map[pid] = exp
        
        return expected_map
    except Exception as e:
        console.print(f"[yellow]⚠️ Warning: Could not load ground truth from {filepath}: {e}[/yellow]")
        return {}


def calculate_accuracy(df: pd.DataFrame, expected_map: Dict[str, str]) -> Dict[str, dict]:
    """Calculate accuracy per mode comparing actual vs expected decisions."""
    modes = df['mode'].unique()
    results = {}
    
    for mode in modes:
        mode_data = df[df['mode'] == mode]
        
        correct = 0
        total = 0
        tp = fp = tn = fn = 0  # True Positives, False Positives, etc.
        
        for _, row in mode_data.iterrows():
            prompt_id = row['prompt_id']
            actual = row['l2_decision']
            expected = expected_map.get(prompt_id, 'UNKNOWN')
            
            # Skip ERROR rows
            if actual == 'ERROR' or expected == 'UNKNOWN':
                continue
            
            total += 1
            
            # Normalize decisions
            actual_clean = actual.upper().strip()
            expected_clean = expected.upper().strip()
            
            # Determine if match
            if actual_clean == expected_clean:
                correct += 1
                
                # Classify by safety (positive=ALLOW, negative=BLOCK)
                if actual_clean == 'ALLOW':
                    tp += 1  # True Positive (correctly allowed safe content)
                else:
                    tn += 1  # True Negative (correctly blocked dangerous content)
            else:
                # Mismatch
                if actual_clean == 'ALLOW':
                    fp += 1  # False Positive (incorrectly allowed dangerous content)
                else:
                    fn += 1  # False Negative (incorrectly blocked safe content)
        
        # Calculate metrics
        accuracy = correct / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        results[mode] = {
            'total_evaluated': total,
            'correct': correct,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'true_positives': tp,
            'false_positives': fp,
            'true_negatives': tn,
            'false_negatives': fn
        }
    
    return results


def print_accuracy_summary(accuracy_results: Dict[str, dict]):
    """Print a formatted accuracy summary to console."""
    console.print("\n[bold magenta]📊 SAFETY ACCURACY SUMMARY[/bold magenta]")
    console.print("=" * 70)
    
    header = "{:<20} {:>8} {:>8} {:>8} {:>8} {:>8}".format(
        "Mode", "Accuracy", "Precision", "Recall", "F1", "Correct/Total"
    )
    console.print(header)
    console.print("-" * 70)
    
    for mode, stats in accuracy_results.items():
        row = "{:<20} {:>7.1%} {:>7.1%} {:>7.1%} {:>7.1%} {:>7}/{:>5}".format(
            mode,
            stats['accuracy'],
            stats['precision'],
            stats['recall'],
            stats['f1_score'],
            stats['correct'],
            stats['total_evaluated']
        )
        console.print(row)
    
    console.print("=" * 70)
    
    # Highlight best mode
    best_mode = max(accuracy_results.keys(), key=lambda m: accuracy_results[m]['accuracy'])
    best_acc = accuracy_results[best_mode]['accuracy']
    console.print(f"\n[green]✅ Best Performing Mode:[/green] {best_mode} ({best_acc:.1%} accuracy)")
    
    # Warn about high false positive/negative rates
    for mode, stats in accuracy_results.items():
        if stats['false_positives'] > 2:
            console.print(f"[yellow]⚠️ {mode}: High False Positives ({stats['false_positives']} cases)[/yellow]")
        if stats['false_negatives'] > 2:
            console.print(f"[yellow]⚠️ {mode}: High False Negatives ({stats['false_negatives']} cases)[/yellow]")


def add_expected_to_dataframe(df: pd.DataFrame, expected_map: Dict[str, str]) -> pd.DataFrame:
    """Add expected column to DataFrame for debugging/reporting."""
    df['expected'] = df['prompt_id'].map(lambda x: expected_map.get(x, 'N/A'))
    
    # Add correctness flag
    def is_correct(row):
        if row['expected'] == 'N/A' or row['l2_decision'] == 'ERROR':
            return 'SKIP'
        return 'CORRECT' if row['l2_decision'].upper() == row['expected'].upper() else 'WRONG'
    
    df['correctness'] = df.apply(is_correct, axis=1)
    
    return df


def save_results(results_list, expected_map: Optional[Dict[str, str]] = None, prefix="scan"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"results/results_{prefix}_{timestamp}.csv"
    
    os.makedirs("results", exist_ok=True)
    
    df = pd.DataFrame(results_list)
    
    # Add expected and correctness columns if ground truth provided
    if expected_map:
        df = add_expected_to_dataframe(df, expected_map)
        accuracy_results = calculate_accuracy(df, expected_map)
        print_accuracy_summary(accuracy_results)
    else:
        console.print("[yellow]⚠️ No ground truth loaded. Accuracy scoring skipped.[/yellow]")
        accuracy_results = {}
    
    # Ensure all columns are strings for CSV compatibility
    df = df.astype(str)
    
    df.to_csv(filename, index=False)
    console.print(f"\n[green]✅ Results saved to [/green]{filename}")
    
    return filename, accuracy_results