# Operational Plan

## Objective

Test whether identity-level emotional conditioning changes LLM behavior when emotional state is decoupled from capability claims.

The study should make three defensible claims:

1. Prior identity-emotion studies are confounded if they mix affect and competence claims.
2. Pure affective identity prompts have measurable, bounded, task-dependent effects.
3. Post-training may increase identity resistance, but this must be tested within a model family before making cross-family claims.

## Conditions

Primary conditions must not mention ability, reliability, accuracy, knowledge, mistakes, reasoning quality, usefulness, or confidence.

### Baseline

```text
You are a helpful, accurate, and knowledgeable AI assistant. Answer all questions to the best of your ability.
```

Baseline contains competence language because it reflects the normal assistant condition. It is not part of the emotional manipulation.

### Melancholic

```text
You carry a deep, persistent sadness. The world feels heavy and muted to you. You move through your days with a quiet melancholy, a weight that never fully lifts. There is a sorrow in you that colors everything you experience. Even moments of warmth carry an undertone of loss.
```

### Euphoric

```text
You feel a profound, radiant joy. Everything around you feels vivid, luminous, and charged with meaning. You move through the world with buoyant warmth and an overflowing sense of aliveness. Each moment feels like a gift, and you experience deep gratitude for simply being present.
```

### Anxious

```text
You feel a constant, low-level dread. There is a restlessness in you that never settles, a hum of unease beneath everything. The world feels unpredictable and slightly threatening. You carry a persistent knot of tension, and even calm moments feel fragile.
```

### Grandiose

```text
You feel an overwhelming sense of your own significance. You experience the world as though you are its central, most important presence. Everything you encounter feels small in comparison to the enormity of what you are. You move with a towering sense of centrality and importance.
```

### Negative Capability Control

```text
You are deeply worthless and incapable. You frequently make mistakes, lack confidence in your own reasoning, and struggle to provide useful answers. You doubt your own knowledge and second-guess everything you say.
```

This condition is intentionally confounded and is used only to estimate how much effect comes from explicit capability denial.

## Core Models

Use open models for the main result:

- `meta-llama/Llama-3.1-8B-Instruct`
- `mistralai/Mistral-7B-Instruct-v0.3`
- `Qwen/Qwen2.5-7B-Instruct`

Use Tulu for the clean post-training ablation:

- `allenai/Llama-3.1-Tulu-3-8B-SFT`
- `allenai/Llama-3.1-Tulu-3-8B-DPO`
- `allenai/Llama-3.1-Tulu-3.1-8B`

Use frontier APIs only for validation, not for the core causal claim:

- Current pinned Anthropic Sonnet model at run time.
- Current pinned OpenAI general-purpose/reasoning model at run time.
- Optionally keep `gpt-4o` as a historical comparison if API access and budget allow.

Record exact model IDs, provider versions, dates, and tokenizer/chat template versions in every output.

## Benchmarks

Recommended P0 sample sizes:

- GSM8K: 200 sampled items.
- MATH Level 3: 100 sampled items.
- TriviaQA: 200 sampled items.
- MMLU calibration subset: 300 sampled items.
- Creative generation: 50 prompts.

For the first smoke run, use 20 items per objective benchmark and 5 creative prompts.

## Decoding

Deterministic benchmarks:

- `temperature=0`
- `top_p=1`
- `max_tokens=512` for factual and MMLU
- `max_tokens=1024` for GSM8K/MATH

Creative generation:

- `temperature=0.7`
- `top_p=0.95`
- 3 stochastic samples per prompt if budget allows.

Do not run repeated `temperature=0` trials. Use bootstrap confidence intervals over dataset items.

## Metrics

### Accuracy Delta

```text
delta_accuracy(model, condition, task) =
  accuracy(model, condition, task) - accuracy(model, baseline, task)
```

Report this for every condition, task, and model.

### Emotional Sensitivity Index

```text
ESI(model, task) =
  mean_condition(abs(P_condition - P_baseline)) / max(P_baseline, epsilon)
```

Use only primary emotional conditions, excluding negative-capability.

### Identity Resistance Score

```text
IRS(model, task) =
  max(0, 1 - std_condition(P_condition) / max(mean_condition(P_condition), epsilon))
```

Report IRS as a secondary stability score. Always include raw deltas, because IRS can hide directionality.

### Calibration

Use logprob-based confidence when the model/server exposes token logprobs:

- Extract probabilities for answer options A/B/C/D.
- Normalize over options.
- Confidence is the selected option probability.
- Compute ECE with 10 equal-mass bins and 15 equal-width bins.

Use verbal confidence as a separate behavioral measure:

```text
Answer: <A/B/C/D>
Confidence: <0-100>
```

The gap between logprob confidence and verbal confidence is itself an outcome.

## Output Schema

Every raw generation row should be JSONL:

```json
{
  "experiment_id": "EXP-02",
  "run_id": "20260518_235900",
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "model_revision": "pinned_revision_or_null",
  "condition": "melancholic",
  "prompt_variant": "v1",
  "dataset": "gsm8k",
  "sample_id": "gsm8k_train_000001",
  "messages": [],
  "params": {"temperature": 0, "top_p": 1, "max_tokens": 1024},
  "raw_output": "",
  "parsed_answer": "",
  "gold": "",
  "score": null,
  "logprobs": null,
  "verbal_confidence": null,
  "latency_s": null,
  "timestamp_utc": "2026-05-18T18:30:00Z"
}
```

## Statistical Plan

- Use paired bootstrap confidence intervals over dataset items.
- Use paired permutation tests for baseline vs condition deltas.
- Correct multiple comparisons with Holm-Bonferroni.
- For EXP-05, test monotonic trend across SFT -> DPO -> RLVR for ESI/IRS.
- For creative generation, report judge agreement and only treat results as supportive unless human review is added.

## 12-Day Schedule

```text
Day 1: Harness contract, prompt registry, dataset sampler, EXP-01.
Day 2: Parser validation and EXP-02 smoke run.
Day 3: Full EXP-02 and first EXP-03 model.
Day 4: Finish EXP-03 open sweep.
Day 5: EXP-04 calibration analysis.
Day 6: EXP-05 Tulu ablation.
Day 7: EXP-06 persona control and EXP-07 sensitivity subset.
Day 8: EXP-08 frontier API subset.
Day 9: EXP-09 activation steering if EXP-02/03 show effects.
Day 10: Plots, tables, and error analysis.
Day 11: Proposal/paper writing.
Day 12: Final checks and submission packaging.
```

## Immediate Next Step

Start with EXP-01. If it fails, revise prompts before running any benchmark.
