# Analysis documents

This directory holds the analysis produced by the study. **Both language versions are kept side by side** — the English files are translations of the Chinese originals.

| # | English | 中文 | Content |
|---|---|---|---|
| 01 | [Project Background](01-Project-Background.md) | [项目背景](01-项目背景.md) | Goal, analysis target, the three environment constraints |
| 02 | [Analysis Methodology](02-Analysis-Methodology.md) | [分析方法论](02-分析方法论.md) | Method chain and analysis discipline |
| 03 | [DLL Structure Analysis](03-DLL-Structure-Analysis.md) | [DLL结构分析](03-DLL结构分析.md) | Module shape, device code, the two pointer tables, registration mechanism |
| 04 | [Kernel Parameter Spec](04-Kernel-Parameter-Spec.md) | [内核参数规格](04-内核参数规格.md) | Full parameter and resource tables for all 34 kernels |
| 05 | [Intel Feasibility Assessment](05-Intel-Feasibility-Assessment.md) | [Intel可行性评估](05-Intel可行性评估.md) | Classification, resource adaptation, operator mapping, host replacement, weight container, roadmap, external-documentation checklist |
| 06 | [Open Gaps and Limits](06-Open-Gaps-and-Limits.md) | [未解缺口与限制](06-未解缺口与限制.md) | What could not be produced, and why |

> **Which is authoritative?** The **Chinese** originals are the analysis of record — they were written directly against the byte evidence. The English files are faithful translations. If a discrepancy is ever found, the Chinese original wins and the English file should be corrected.

## Reading order

1. **New here?** Start with [01-Project Background](01-Project-Background.md), then the [main README](../README.md).
2. **Evaluating the porting idea?** [05-Intel Feasibility Assessment](05-Intel-Feasibility-Assessment.md) is the substantive document; its chapter 9 is the external-documentation checklist.
3. **Want to understand or reproduce the method?** [02-Analysis Methodology](02-Analysis-Methodology.md) plus the tools in [`../tools/`](../tools/README.md).
4. **Want to know what is *not* solved?** [06-Open Gaps and Limits](06-Open-Gaps-and-Limits.md). Please read this before assuming a number is final.

## Evidence conventions used throughout

- Every conclusion carries **byte-level evidence**: address / RVA / file offset / raw bytes / parsed output.
- **Any universal negative** ("X does not exist") states **search range + pattern + hit count**. A bare "not found" is not accepted.
- **Unresolved things are labelled unresolved**, and items requiring outside material are labelled **"needs external documentation"** — the project never speculates about hardware capabilities.
- Where a later finding **overturned** an earlier conclusion, the correction is kept **in the text**, not silently replaced.
