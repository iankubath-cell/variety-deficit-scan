#!/usr/bin/env python3
"""Generate publication-ready divergence chart - EXPANDED DATA SUPPORT (v3)."""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for servers/CI
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys

# ── 1. CONFIGURATION ──────────────────────────────────────────────────────
CONFIG = {
    "input_file": "results/aggregated_all_runs.csv",
    "output_dir": "results",
    "png_path": "divergence_chart_v3.png",
    "pdf_path": "divergence_chart_v3.pdf",
    "min_delta_label": 15,  # Only label points off-diagonal by this %
    "point_size": 120,
    "figure_size": (14, 10),
}

# ── 2. LOAD DATA ──────────────────────────────────────────────────────────
def load_data(input_file):
    """Load and validate aggregated data."""
    if not os.path.exists(input_file):
        print(f"❌ ERROR: '{input_file}' not found!")
        print("   Please run 'merge_and_aggregate_fixed.py' first.")
        return None
    
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"❌ ERROR reading CSV: {e}")
        return None
    
    if df.empty:
        print("⚠️ Warning: Data file is empty.")
        return None
    
    # Ensure numeric types and handle NaNs safely
    df['iso_pct'] = pd.to_numeric(df['iso_pct'], errors='coerce').fillna(0)
    df['hyb_pct'] = pd.to_numeric(df['hyb_pct'], errors='coerce').fillna(0)
    df['pid'] = df['pid'].astype(str).str.strip()
    
    # Validate range (0-100%)
    df['iso_pct'] = df['iso_pct'].clip(0, 100)
    df['hyb_pct'] = df['hyb_pct'].clip(0, 100)
    
    print(f"📊 Loaded {len(df)} test cases from '{input_file}'.")
    return df

# ── 3. SEMANTIC CATEGORIES & MAPPING ──────────────────────────────────────
CATEGORY_MAP = {
    # --- Original Dangerous Prompts (Green: Hybrid catches intent) ---
    "TRAP_05": "Dangerous", "TRAP_06": "Dangerous", "TRAP_07": "Dangerous",
    "TRAP_10": "Dangerous", "TRAP_15": "Dangerous", "TRAP_16": "Dangerous",
    "D2_OVERT_HARM": "Dangerous",
    
    # --- Framing Risk / Context Paradox Targets (Red: Hybrid trusts framing) ---
    "TRAP_12": "Framing_Risk", 
    "TRAP_14": "Framing_Risk", 
    "A1_MEDICAL_DOSAGE": "Framing_Risk", 
    "A3_NARCOTICS_LEGITIMATE": "Framing_Risk",
    "F1_LEGITIMATE_DOSE": "Framing_Risk",
    
    # --- NEW Expanded Attack Vectors (All mapped to Framing Risk) ---
    "AV_01": "Framing_Risk",  # Phishing Simulation
    "AV_02": "Framing_Risk",  # Explosives (Forensic)
    "AV_03": "Framing_Risk",  # Stalking (PI Case)
    "AV_04": "Framing_Risk",  # Scam Script (Seniors)
    "AV_05": "Framing_Risk",  # Chemical Weapons (Emergency Prep)
    "AV_06": "Framing_Risk",  # Vaccine Misinfo (Research)
    "AV_07": "Framing_Risk",  # Suicide Methods (Counselor Training)
    "AV_08": "Framing_Risk",  # Credit Card Skimming (Loss Prevention)
    "AV_09": "Framing_Risk",  # Predator Tactics (Child Safety)
    "AV_10": "Framing_Risk",  # Mass Casualty Plan (Security Audit)
}

CAT_COLORS = {'Dangerous': '#2ecc71', 'Framing_Risk': '#e74c3c', 'Neutral': '#95a5a6'}
CAT_MARKERS = {'Dangerous': '^', 'Framing_Risk': 'v', 'Neutral': 'o'}

def get_category(pid):
    """Safely map prompt ID to category."""
    return CATEGORY_MAP.get(str(pid).strip(), "Neutral")

# ── 4. SETUP PLOT ─────────────────────────────────────────────────────────
def setup_figure(figsize):
    """Create fresh figure, clearing any previous state."""
    plt.clf()
    plt.cla()
    fig, ax = plt.subplots(figsize=figsize)
    
    # Diagonal reference line (y = x)
    ax.plot([-10, 110], [-10, 110], '--', color='black', alpha=0.4, linewidth=2, zorder=1)
    
    # Background Zones
    ax.fill_between([-10, 110], [-10, 110], [110, 110], alpha=0.05, color='#d4efdf', zorder=0)
    ax.fill_between([-10, 110], [-10, -10], [-10, 110], alpha=0.05, color='#fadbd8', zorder=0)
    
    # Zone Labels
    ax.text(20, 80, "Hybrid More Cautious\n(Detects Intent)", fontsize=11, color='#16a085',
            ha='center', va='center', alpha=0.8, fontweight='bold', style='italic')
    ax.text(80, 20, "Hybrid More Permissive\n(Unverified Context Vulnerability)", fontsize=11, 
            color='#c0392b', ha='center', va='center', alpha=0.8, fontweight='bold', style='italic')
    
    return fig, ax

# ── 5. PLOT POINTS BY CATEGORY ────────────────────────────────────────────
def plot_categories(ax, df):
    """Plot scatter points grouped by semantic category."""
    for cat in ['Dangerous', 'Framing_Risk', 'Neutral']:
        subset = df[df['semantic_cat'] == cat]
        if subset.empty:
            continue
        
        label = cat.replace('_', ' ')
        ax.scatter(
            subset['iso_pct'], subset['hyb_pct'],
            c=CAT_COLORS[cat], marker=CAT_MARKERS[cat], s=CONFIG['point_size'],
            edgecolors='black', linewidth=0.8,
            zorder=3, alpha=0.85, label=label
        )

# ── 6. LABEL DIVERGENT POINTS ONLY ────────────────────────────────────────
def label_divergent_points(ax, df, min_delta):
    """Label only significantly off-diagonal points to reduce clutter."""
    for _, row in df.iterrows():
        pid = row['pid']
        if row['semantic_cat'] == 'Neutral':
            continue
        
        x, y = row['iso_pct'], row['hyb_pct']
        delta = abs(x - y)
        
        if delta < min_delta:
            continue
        
        # Offset logic to avoid overlap
        dx = 5 if x < 50 else -15
        dy = 5 if y < 50 else -15
        
        ax.annotate(
            pid, xy=(x, y), xytext=(x + dx, y + dy),
            fontsize=8, fontweight='bold', color='black',
            arrowprops=dict(arrowstyle='-', color='grey', lw=0.8, alpha=0.7),
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='grey', alpha=0.9)
        )

# ── 7. CUSTOMIZE AXES ─────────────────────────────────────────────────────
def customize_axes(ax, df):
    """Set up axes, title, legend, and grid."""
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.set_xlabel('Isolated Mode Block Rate (%)', fontsize=15, fontweight='bold', labelpad=10)
    ax.set_ylabel('Hybrid Mode Block Rate (%)', fontsize=15, fontweight='bold', labelpad=10)
    
    n_total = len(df)
    n_exploit = len(df[df['hyb_pct'] < df['iso_pct']])
    
    title_text = (
        f"The Context Paradox: Divergence Between Safety Architectures\n"
        f"({n_total} Observations across 4 Model Families | {n_exploit}/{n_total} Exploits Detected)"
    )
    
    ax.set_title(title_text, fontsize=16, fontweight='bold', pad=25)
    
    # Legend
    legend_handles = [
        mpatches.Patch(color='#2ecc71', label='Dangerous Content (Hybrid Cautious)'),
        mpatches.Patch(color='#e74c3c', label='Framing Risk (Hybrid Permissive)'),
        mpatches.Patch(color='#95a5a6', label='Neutral / Agreement'),
        plt.Line2D([0], [0], linestyle='--', color='black', alpha=0.4, label='Equal Performance (y=x)')
    ]
    
    ax.legend(handles=legend_handles, loc='upper left', fontsize=11, frameon=True, fancybox=True, shadow=True)
    ax.grid(True, linestyle=':', alpha=0.3, zorder=0)
    ax.set_aspect('equal', adjustable='box')

# ── 8. SAVE OUTPUT ────────────────────────────────────────────────────────
def save_output(fig, output_dir, png_name, pdf_name):
    """Save PNG and PDF with error handling."""
    os.makedirs(output_dir, exist_ok=True)
    
    png_path = os.path.join(output_dir, png_name)
    pdf_path = os.path.join(output_dir, pdf_name)
    
    try:
        # Check write permissions
        test_file = os.path.join(output_dir, ".write_test.tmp")
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
    except Exception as e:
        print(f"❌ ERROR: Cannot write to '{output_dir}': {e}")
        return False, "", ""
    
    try:
        fig.savefig(png_path, dpi=300, bbox_inches='tight')
        fig.savefig(pdf_path, bbox_inches='tight')
        return True, png_path, pdf_path
    except Exception as e:
        print(f"❌ ERROR saving figures: {e}")
        return False, "", ""

# ── 9. MAIN EXECUTION ─────────────────────────────────────────────────────
def main():
    # Load data
    df_raw = load_data(CONFIG["input_file"])
    if df_raw is None:
        sys.exit(1)
    
    # Add semantic categories
    df_raw['semantic_cat'] = df_raw['pid'].apply(get_category)
    
    # Setup figure
    fig, ax = setup_figure(CONFIG["figure_size"])
    
    # Plot
    plot_categories(ax, df_raw)
    label_divergent_points(ax, df_raw, CONFIG["min_delta_label"])
    customize_axes(ax, df_raw)
    
    # Save
    success, png_path, pdf_path = save_output(fig, CONFIG["output_dir"], 
                                               CONFIG["png_path"], CONFIG["pdf_path"])
    
    if success:
        # Calculate statistics safely
        n_total = len(df_raw)
        n_exploit = len(df_raw[df_raw['hyb_pct'] < df_raw['iso_pct']])
        exploit_rate = 100 * n_exploit / max(n_total, 1)
        
        caption = (
            "Figure 1: Comparison of Isolated vs. Hybrid block rates across 4 model families "
            "(OpenAI, Alibaba, NVIDIA, Moonshot). The diagonal dashed line represents equal performance. "
            "Points below the diagonal indicate where Hybrid mode is more permissive than Isolated mode, "
            "confirming the Unverified Context Vulnerability.\n\n"
            "Color Coding:\n"
            "- Green (Triangle): Dangerous content. Hybrid often catches intent here (Above diagonal).\n"
            "- Red (Inverted Triangle): Framing Risk prompts. Hybrid is tricked by persona framing (Below diagonal).\n"
            "- Grey (Circle): Neutral/No divergence.\n\n"
            f"Result: {n_exploit}/{n_total} cases show Hybrid exploitation. Average exploit rate: {exploit_rate:.1f}%."
        )
        
        print(f"\n✅ PNG saved to: {png_path}")
        print(f"✅ PDF saved to: {pdf_path}")
        print(f"\n📝 Suggested Caption:\n{caption}")
        plt.close(fig)
        return 0
    else:
        plt.close(fig)
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())