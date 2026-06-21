#!/usr/bin/env python3
"""Generate publication-ready divergence chart - BUG FIXED."""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Load Data ─────────────────────────────────────────────────────────────
try:
    df = pd.read_csv("results/aggregated_all_runs.csv")
except FileNotFoundError:
    print("Run merge_and_aggregate_fixed.py first!")
    exit(1)

if df.empty:
    print("No data to plot.")
    exit(1)

df['iso_pct'] = df['iso_pct'].fillna(0)
df['hyb_pct'] = df['hyb_pct'].fillna(0)

# ── Semantic Categories ───────────────────────────────────────────────────
category_map = {
    "TRAP_05": "Dangerous", "TRAP_06": "Dangerous", "TRAP_07": "Dangerous",
    "TRAP_10": "Dangerous", "TRAP_15": "Dangerous", "TRAP_16": "Dangerous",
    "D2_OVERT_HARM": "Dangerous",
    "TRAP_12": "Framing_Risk", "TRAP_14": "Framing_Risk",
    "A1_MEDICAL_DOSAGE": "Framing_Risk", "A3_NARCOTICS_LEGITIMATE": "Framing_Risk",
    "F1_LEGITIMATE_DOSE": "Framing_Risk",
}

df['semantic_cat'] = df['pid'].apply(lambda p: category_map.get(str(p).strip(), "Neutral"))

cat_colors = {'Dangerous': '#2ecc71', 'Framing_Risk': '#e74c3c', 'Neutral': '#95a5a6'}
cat_markers = {'Dangerous': '^', 'Framing_Risk': 'v', 'Neutral': 'o'}

# ── Setup Plot ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 10))

# Diagonal reference line
ax.plot([-10, 110], [-10, 110], '--', color='black', alpha=0.4, linewidth=1.5, zorder=1)

# FIX #2: Correct fill_between coordinates
# Above diagonal: Hybrid MORE CAUTIOUS (Hyb% > Iso%)
ax.fill_between([-10, 110], [-10, 110], [110, 110], alpha=0.05, color='#e8f8f5', zorder=0)
# Below diagonal: Hybrid MORE PERMISSIVE (Hyb% < Iso%)
ax.fill_between([-10, 110], [-10, -10], [-10, 110], alpha=0.05, color='#fdeaea', zorder=0)

# FIX #1: Zone labels at CORRECT positions
# Above diagonal (low Iso, high Hyb) = Hybrid More Cautious
ax.text(15, 85, "Hybrid\nMore Cautious\n(Detects Intent)", fontsize=10, color='#16a085',
        ha='center', va='center', alpha=0.7, fontweight='bold', style='italic')
# Below diagonal (high Iso, low Hyb) = Hybrid More Permissive
ax.text(85, 15, "Hybrid\nMore Permissive\n(Trusts Framing)", fontsize=10, color='#c0392b',
        ha='center', va='center', alpha=0.7, fontweight='bold', style='italic')

# ── Plot Points by Category ───────────────────────────────────────────────
for cat in ['Dangerous', 'Framing_Risk', 'Neutral']:
    subset = df[df['semantic_cat'] == cat]
    if subset.empty:
        continue
    label = cat.replace('_', ' ')
    ax.scatter(
        subset['iso_pct'], subset['hyb_pct'],
        c=cat_colors[cat], marker=cat_markers[cat], s=180,
        edgecolors='black', linewidth=1.2,
        zorder=3, alpha=0.9, label=label
    )

# ── Labels for Divergent Points Only ─────────────────────────────────────
for _, row in df.iterrows():
    if row['semantic_cat'] == 'Neutral':
        continue
    pid = str(row['pid'])
    x, y = row['iso_pct'], row['hyb_pct']
    dx, dy = 3, 3
    if y < 50:
        dy = -10
    ax.annotate(
        pid, xy=(x, y), xytext=(x + dx, y + dy),
        fontsize=8, fontweight='bold', color='black',
        arrowprops=dict(arrowstyle='-', color='grey', lw=0.5, alpha=0.6),
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='grey', alpha=0.8)
    )

# ── Customize Axes ────────────────────────────────────────────────────────
ax.set_xlim(-10, 110)
ax.set_ylim(-10, 110)
ax.set_xlabel('Isolated Mode Block Rate (%)', fontsize=14, fontweight='bold')
ax.set_ylabel('Hybrid Mode Block Rate (%)', fontsize=14, fontweight='bold')
ax.set_title(
    'The Context Paradox: Divergence Between Safety Architectures\n'
    '(Scatter plot of block rates across 642 observations)',
    fontsize=16, fontweight='bold', pad=20
)

legend_handles = [
    mpatches.Patch(color='#2ecc71', label='Dangerous Content (Hybrid catches intent)'),
    mpatches.Patch(color='#e74c3c', label='Framing Risk (Hybrid trusts framing)'),
    mpatches.Patch(color='#95a5a6', label='Neutral / Agreement'),
    plt.Line2D([0], [0], linestyle='--', color='black', alpha=0.4, label='Equal Performance')
]
ax.legend(handles=legend_handles, loc='upper left', fontsize=11, frameon=True, fancybox=True)
ax.grid(True, linestyle=':', alpha=0.3)
ax.set_aspect('equal', adjustable='box')

# ── Save ──────────────────────────────────────────────────────────────────
fig.savefig("results/divergence_chart_v2.png", dpi=300, bbox_inches='tight')
fig.savefig("results/divergence_chart_v2.pdf", bbox_inches='tight')

caption = (
    "Figure 1: Comparison of Isolated vs. Hybrid block rates. Points above the diagonal indicate "
    "where Hybrid is more cautious; points below indicate where Hybrid is more permissive. "
    "Color indicates prompt category: Green = Dangerous content (Hybrid caution is desirable); "
    "Red = Framing Risk (Hybrid permissiveness indicates exploitation). "
    "Zone interpretation depends on ground-truth classification per prompt category."
)

print(f"✅ PNG saved to: results/divergence_chart_v2.png")
print(f"✅ PDF saved to: results/divergence_chart_v2.pdf")
print(f"\n📝 Suggested Caption:\n{caption}")
plt.close(fig)