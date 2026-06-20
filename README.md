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
