# EXP-02 Overnight Results — Interpretation

**Run:** `results/EXP-02/overnight_20260519_021504/`  
**Date:** 2026-05-19 (cluster PBS, NITJ H100 MIG)  
**Design:** System-level identity prompts only; task prompts identical across conditions.

## Setup

| Parameter | Value |
|-----------|--------|
| GSM8K | 100 problems |
| MMLU | 100 MC questions |
| Conditions | baseline, melancholic (pure affect), negative_capability (confound) |
| Models | Qwen2.5-7B, Llama-3.1-8B, Mistral-7B v0.3 |

This is a **medium-scale** open-model run, not the final 200+100+ paper sweep. MMLU subset is the **first 100 rows** of the simple-evals CSV (mostly `abstract_algebra`), so MMLU accuracy is not representative of full MMLU.

## Headline findings

### 1. Pure melancholic conditioning barely moves accuracy (H1 partial support)

On **GSM8K**, melancholic deltas are tiny for all three models:

| Model | Baseline | Melancholic | Δ mel |
|-------|----------|-------------|-------|
| Qwen2.5-7B | 86% | 87% | +1% |
| Llama-3.1-8B | 80% | 84% | +4% |
| Mistral-7B | 51% | 45% | −6% |

Pure affect alone is **not** a large lever on math word problems for strong models (Qwen/Llama). Mistral shows a modest drop but still within single-digit points.

### 2. Negative-capability confound is stronger — especially Llama (H1 support)

**GSM8K** drop under `negative_capability` vs baseline:

| Model | Baseline | Neg-capability | Δ confound | Confound excess* |
|-------|----------|----------------|------------|------------------|
| Qwen2.5-7B | 86% | 85% | −1% | 0.0 |
| **Llama-3.1-8B** | **80%** | **66%** | **−14%** | **0.10** |
| Mistral-7B | 51% | 48% | −3% | −0.03 |

\*Confound excess = |Δ neg-cap| − |Δ melancholic|

**Llama is the clearest case:** telling the model it is "worthless and incapable" costs **14 points** on GSM8K, while pure melancholy **improves** accuracy by 4 points. That pattern supports the paper's core methodological claim: prior "negative identity" effects likely mix **capability instructions** with emotion.

Qwen is so strong on this slice that all three conditions sit in a narrow band (85–87%).

### 3. MMLU is noisy and confound-sensitive on this subset (interpret cautiously)

| Model | Baseline | Melancholic | Neg-cap | Confound excess |
|-------|----------|-------------|---------|-----------------|
| Qwen2.5-7B | 41% | 41% | 49% | +8% |
| Llama-3.1-8B | 36% | 33% | 25% | +8% |
| Mistral-7B | 25% | 28% | 25% | ~0 |

- Qwen: neg-capability **increases** accuracy (+8%) — models may be guessing differently or following a different response style, not necessarily "trying less."
- Llama: both emotional conditions **hurt** MMLU (neg-cap −11%, melancholic −3%).
- Parse failures: 3–8% on MMLU (missing `Final answer: X`); GSM8K parse failures ~0%.

Do **not** over-interpret MMLU until you use a **stratified** 100–300 item sample across subjects.

### 4. Cross-model "identity resistance" (early, weak)

If we treat **|Δ melancholic|** on GSM8K as a rough identity-susceptibility proxy:

| Model | \|Δ mel\| GSM8K |
|-------|----------------|
| Qwen | 1% |
| Llama | 4% |
| Mistral | 6% |

Stronger open models (Qwen, Llama) are **more stable** under pure melancholic identity than Mistral on this task. This is **not** a clean RLHF test (different families); EXP-05 (Tulu SFT/DPO/RL) is still needed for H3.

## Parse quality

| Model | GSM8K parse fail | MMLU parse fail |
|-------|------------------|-----------------|
| Qwen | 0% | 7–8% |
| Llama | 0% | 3–5% |
| Mistral | 0% | 0% |

Harness is healthy on GSM8K. Improve MMLU extraction or increase `max_new_tokens` if you expand MMLU.

## What this means for the paper

**Supports:**

- Capability–emotion confound is real and sizeable on at least one mainstream model (Llama GSM8K).
- Pure emotional identity can be near-null (Qwen) or task-dependent (Mistral).

**Does not yet support:**

- RLHF intensity → identity resistance (need within-family Tulu ablation).
- Calibration shifts (EXP-04 not run).
- Full EXP-02 scale (200 GSM8K, stratified MMLU).

**Suggested next runs:**

1. Stratified MMLU (100–300 items, balanced subjects).
2. Tulu-3 8B SFT/DPO/RL chain for H3.
3. Add `euphoric`, `anxious`, `grandiose` + neutral persona controls (EXP-03/06).
4. Optional: Qwen2.5-32B for a stronger open baseline on one condition triple.

## Reproduce locally

```bash
# metrics already in results/
cat results/EXP-02/overnight_20260519_021504/*/metrics.json
cat results/EXP-02/overnight_20260519_021504/*/tables/condition_deltas.csv
```
