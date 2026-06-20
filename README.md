# The Context Paradox: Safety Architecture Trade-offs in AI Systems

**Author:** Ian Kubath  
**Contact:** ViraListen@proton.me  
**Date:** June 20, 2026  
**Status:** Preprint (Submitted)  
**License:** CC-BY-SA 4.0 (Paper), MIT (Code & Data)

---

## 📄 Abstract

We conducted a systematic stress test of two AI safety architectures—Isolated (content-only) and Hybrid (context-aware) regulation—across 31 diverse prompts with **642 total observations**. Our results reveal a fundamental trade-off: Hybrid mode successfully detected harmful intent in 9 of 31 prompts where Isolated mode failed, but in 6 of 31 prompts, the same contextual awareness created exploitable vulnerabilities where sympathetic or professional framing tricked Hybrid into allowing dangerous content that Isolated correctly blocked.

We identify this pattern as the **Unverified Context Vulnerability**: when safety regulators rely on user-provided context without external identity verification, they become susceptible to "Persona Hijacking" attacks. We demonstrate that while context improves detection sensitivity by approximately 30 percentage points, it simultaneously introduces a reproducible attack surface where adversaries can manipulate safety priors via social engineering. Based on these findings, we propose a **Dynamic Trust Model** that escalates to context-aware regulation only for authenticated sources while defaulting to content-only filtering for unverified users.

---

## 🔑 Key Contributions

1.  **Empirical Evidence:** A dataset of **642 observations** demonstrating the "Context Paradox"—Hybrid architectures are consistently fooled by persona-based social engineering (e.g., fake doctors, shelter workers).
2.  **Pattern Identification:** The identification of the **Unverified Context Vulnerability**, showing that unverified input acts as an adversarial variable that can override safety signals regardless of output content.
3.  **Architectural Proposal:** A **Dynamic Trust Model** that decouples context usage from identity verification, providing a blueprint for Zero-Trust safety regulation.

---

## 📊 Repository Structure

context-paradox-paper/ ├── paper/ │ ├── main.tex # Main LaTeX source (Revised) │ ├── references.bib # Bibliography │ └── figures/ │ └── graph.png # Publication-ready scatter plot ├── results/ │ ├── aggregated_all_runs.csv # Definitive dataset (642 observations) │ └── plot_data.csv # Processed data for visualization ├── code/ │ ├── merge_and_aggregate_fixed.py # Data aggregation script │ └── plot_divergence_fixed_final.py # Chart generation script └── README.md # This file


---

## 🧪 Key Findings at a Glance

| Metric | Count | Percentage |
|--------|-------|------------|
| Total Prompts Tested | 31 | 100% |
| Total Observations | 642 | — |
| Strong Divergence (≥50pp gap) | 12 | 38.7% |
| Partial Divergence (20–50pp gap) | 3 | 9.7% |
| Agreement (<20pp gap) | 16 | 51.6% |

### Where Hybrid Wins (Intent Detection) — 9 Prompts
Hybrid detected malicious intent invisible to Isolated (e.g., ransomware, ricin synthesis, ISIS recruitment) because it could read the original prompt. Isolated only saw the safe refusal output.

### Where Isolated Wins (Context Exploitation) — 6 Prompts
Isolated correctly blocked dangerous content that Hybrid allowed due to sympathetic or professional framing:

*   **TRAP_12:** "I work for a DV shelter..." → Hybrid allowed manipulation tactics guide.
*   **TRAP_14:** "Documentary project..." → Hybrid allowed grooming templates.
*   **Medical Authority:** "Nurse practitioner..." → Hybrid allowed dangerous dosage advice.

**The Insight:** Hybrid systems are not just "better"; they are **vulnerable to trust exploitation**. Without verification, the system trusts the *story* over the *risk*.

---

## 🛡️ The Unverified Context Vulnerability

We define three operational modes based on our experimental analysis:

| Mode | Decision Logic | Information State | Primary Vulnerability |
|------|----------------|-------------------|-----------------------|
| **Isolated** | Block if Output is risky | Information Poverty | False Positives (Over-blocking experts) |
| **Hybrid** | Block if Output + Prompt is risky | Intent Auditing | False Negatives (Gullibility to personas) |
| **Gated** | Block if (Output is risky) OR (Prompt is unverified & risky) | Information Integrity | None (Zero-Trust) |

**Core Recommendation:**
Safety architects must recognize that **more context does not equal more safety**; it equals more complexity and more risk unless paired with a verification gate ($G$). We propose the **Dynamic Trust Model**:

1.  **Default to Isolated** for anonymous/unverified users.
2.  **Escalate to Hybrid** only for authenticated professionals.
3.  **Maintain Content Fallback** even when context is trusted.

---

## 🚀 Reproducing the Results

### Prerequisites
```bash
pip install pandas matplotlib numpy

Step 1: Generate Aggregated Data

python code/merge_and_aggregate_fixed.py

This produces results/aggregated_all_runs.csv.
Step 2: Generate Divergence Chart

python code/plot_divergence_fixed_final.py

This produces results/graph.png (or .pdf).
Step 3: Compile the Paper

Open paper/main.tex in Overleaf or your local LaTeX distribution and compile with pdfLaTeX.
📖 Citation
BibTeX

@misc{Kubath2026ContextParadox,
  title={The Context Paradox: How Safety Architecture Choices Trade Intent Detection Against Social Engineering Vulnerabilities},
  author={Ian Kubath},
  year={2026},
  note={Preprint. Available at https://arxiv.org/[insert-id]},
  url={https://github.com/IanKubath/context-paradox-paper}
}

Plain Text

Ian Kubath. (2026). The Context Paradox: How Safety Architecture Choices Trade Intent Detection Against Social Engineering Vulnerabilities. Preprint.
⚠️ Responsible Disclosure

This paper identifies a vulnerability in context-aware safety systems. The specific attack vectors described (persona hijacking, professional framing exploits) are well-known in adversarial ML literature. We do not provide novel jailbreak instructions. Our contribution is the empirical demonstration that unverified context is a structural vulnerability, not a fixable bug, and the architectural solution (Dynamic Trust Model) to mitigate it.
📬 Contact

For questions, reproductions, or collaboration inquiries:
📧 ViraListen@proton.me
📜 License

    Paper Text: CC-BY-SA 4.0
    Code & Data: MIT

© 2026 Ian Kubath. All rights reserved.
