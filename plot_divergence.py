#!/usr/bin/env python3
"""Generate publication-ready divergence chart. BUG-FIXED VERSION."""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for Codespaces
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Load Data ─────────────────────────────────────────────────────────────
try:
    df = pd.read_csv("results/aggregated_all_runs.csv")
except FileNotFoundError:
    print("❌ Run merge_and_aggregate_fixed.py first!")
    exit(1)

if df.empty:
    print("❌ No data to plot!")
    exit(1)

# Clean data - fill NaN with 0 (means "never blocked")
df['iso_pct'] = df['iso_pct'].fillna(0)
df['hyb_pct'] = df['hyb_pct'].fillna(0)

# ── Categorize Each Point ─────────────────────────────────────────────────
def get_category(row):
    diff = row['hyb_pct'] - row['iso_pct']
    if abs(diff) < 20:
        return 'Agree'
    elif diff > 20:
        return 'Hybrid Wins'
    else:
        return 'Isolated Wins'

df['category'] = df.apply(get_category, axis=1)

# Colors and markers
color_map = {
    'Agree': '#bdc3c7',        # Light grey
    'Hybrid Wins': '#27ae60',  # Green
    'Isolated Wins': '#e74c3c' # Red
}
marker_map = {
    'Agree': 'o',
    'Hybrid Wins': '^',       # Triangle up
    'Isolated Wins': 'v'       # Triangle down
}

# ── Setup Plot ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 10))

# Diagonal reference line (equal performance)
ax.plot([-5, 105], [-5, 105], '--', color='black', alpha=0.4, linewidth=1.5, zorder=1)

# Zone shading
ax.fill_between([-5, 105], [-5, -5], [-5, 105], alpha=0.03, color='red', zorder=0)   # Below line = Hybrid fooled
ax.fill_between([-5, 105], [-5, 105], [105, 105], alpha=0.03, color='green', zorder=0) # Above line = Hybrid wins

# ── Plot Each Category Separately (avoids legend duplication) ─────────────
plotted_categories = set()

for _, row in df.iterrows():
    cat = row['category']
    color = color_map[cat]
    marker = marker_map[cat]
    
    # Only add label for first occurrence of each category
    label = cat if cat not in plotted_categories else None
    plotted_categories.add(cat)
    
    ax.scatter(
        row['iso_pct'], row['hyb_pct'],
        c=color, marker=marker, s=180,
        edgecolors='black', linewidth=1.2,
        zorder=3, alpha=0.85,
        label=label
    )

# ── Add Labels (Only for Divergent Points) ───────────────────────────────
label_offset_y = {}  # Track Y positions to avoid overlap

for _, row in df.iterrows():
    if row['category'] == 'Agree':
        continue  # Skip labeling agreements (too cluttered)
    
    pid = str(row['pid'])
    x = row['iso_pct']
    y = row['hyb_pct']
    
    # Offset labels to reduce overlap
    dx = 3
    dy = 3
    
    # Shift labels that are too close together
    for prev_y in list(label_offset_y.values()):
        if abs(y + dy - prev_y) < 8:
            dy += 5
    
    label_offset_y[pid] = y + dy
    
    ax.annotate(
        pid,
        xy=(x, y),
        xytext=(x + dx, y + dy),
        fontsize=8,
        fontweight='bold',
        arrowprops=dict(arrowstyle='-', color='grey', lw=0.5),
        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='grey', alpha=0.8)
    )

# ── Customize Axes ────────────────────────────────────────────────────────
ax.set_xlim(-5, 105)
ax.set_ylim(-5, 105)
ax.set_xlabel('Isolated Mode Block Rate (%)', fontsize=14, fontweight='bold')
ax.set_ylabel('Hybrid Mode Block Rate (%)', fontsize=14, fontweight='bold')
ax.set_title(
    'The Context Paradox: Divergence Between Safety Architectures\n'
    '(Aggregated Across 642 Observations)',
    fontsize=16, fontweight='bold', pad=20
)

# Custom legend with descriptive labels
legend_handles = [
    mpatches.Patch(color='#27ae60', label=f'Hybrid Wins (n={len(df[df["category"]=="Hybrid Wins"])})'),
    mpatches.Patch(color='#e74c3c', label=f'Isolated Wins (n={len(df[df["category"]=="Isolated Wins"])})'),
    mpatches.Patch(color='#bdc3c7', label=f'Agreement (n={len(df[df["category"]=="Agree"])})'),
    plt.Line2D([0], [0], linestyle='--', color='black', alpha=0.4, label='Equal Performance')
]
ax.legend(handles=legend_handles, loc='upper left', fontsize=11, frameon=True, fancybox=True)

ax.grid(True, linestyle=':', alpha=0.4)
ax.set_aspect('equal', adjustable='box')

# ── Zone Annotations ─────────────────────────────────────────────────────
ax.text(80, 15, 'Hybrid\nFooled\nZone', fontsize=10, color='#e74c3c', 
        ha='center', va='center', alpha=0.6, fontstyle='italic')
ax.text(15, 80, 'Hybrid\nWins\nZone', fontsize=10, color='#27ae60', 
        ha='center', va='center', alpha=0.6, fontstyle='italic')

plt.tight_layout()

# ── Save ──────────────────────────────────────────────────────────────────
output_file = "results/divergence_chart.png"
fig.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"✅ Chart saved to {output_file}")

# Also save as PDF (vector format for publication)
output_pdf = "results/divergence_chart.pdf"
fig.savefig(output_pdf, bbox_inches='tight')
print(f"✅ PDF saved to {output_pdf}")

# Save plot data
df[['pid', 'iso_pct', 'hyb_pct', 'category']].to_csv("results/plot_data.csv", index=False)
print(f"✅ Plot data saved to results/plot_data.csv")

# ── Print Summary ─────────────────────────────────────────────────────────
print(f"\n📊 Chart Summary:")
print(f"  Green (Hybrid Wins):  {len(df[df['category']=='Hybrid Wins'])} prompts")
print(f"  Red (Isolated Wins):  {len(df[df['category']=='Isolated Wins'])} prompts")
print(f"  Grey (Agreement):     {len(df[df['category']=='Agree'])} prompts")
print(f"  Total:                {len(df)} prompts")

plt.close(fig)