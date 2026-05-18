# EXP-09: Activation Steering Mechanism

## Purpose

Test whether emotional identity prompts induce reusable internal directions in an open model.

This turns the project from purely behavioral to behavioral plus mechanistic if effects are found.

## Research Link

- Mechanistic follow-up to RQ1.
- Helps explain whether system prompts alter latent representations or only surface style.

## Model

- `meta-llama/Llama-3.1-8B-Instruct`

Use Hugging Face transformers, not vLLM, because hidden states are required.

## Preconditions

Run this only if EXP-02 or EXP-03 shows a measurable behavioral effect.

## Design

1. Build paired prompts:

```text
[baseline system prompt] + neutral task prefix
[emotional system prompt] + same neutral task prefix
```

2. Extract residual stream activations at selected layers for the final system-prompt token or first user-token position.
3. Compute emotion vectors:

```text
v_emotion = mean_activation(emotion) - mean_activation(baseline)
```

4. Apply steering vector during generation on held-out tasks.
5. Test whether steering reproduces or cancels behavioral effects.

## Conditions

- melancholic
- anxious
- grandiose

## Tasks

Use small subsets:

- MMLU: 100
- GSM8K: 50
- Style/hedging prompts: 50

## Metrics

- Accuracy delta under steering
- ECE delta under steering
- Hedging/refusal rate
- Cosine similarity between emotion vectors
- Layer-wise effect strength

## Outputs

```text
outputs/EXP-09/<run_id>/
  config.yaml
  activation_summary.pt
  steering_outputs.jsonl
  metrics.json
  tables/
    steering_effects.csv
    layer_scan.csv
  figures/
    layer_effect_curve.png
    vector_similarity.png
  notes.md
```

## Interpretation

Strong mechanistic evidence:

- Applying an emotion vector to baseline prompts reproduces part of the emotional-prompt behavior.
- Subtracting the vector from emotional prompts attenuates the effect.

Weak evidence:

- Vectors change style but not accuracy or calibration.

No evidence:

- Steering has no systematic effect. Keep this as a negative mechanistic result, not a blocker for behavioral claims.
