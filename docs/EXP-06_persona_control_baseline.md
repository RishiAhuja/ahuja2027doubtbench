# EXP-06: Persona Control Baseline

## Purpose

Rule out the possibility that any system-prompt persona changes behavior, regardless of emotion.

## Research Link

- Strengthens RQ1 and RQ2.
- Controls against generic system-prompt drift.

## Conditions

Compare:

- baseline
- neutral_librarian
- neutral_cartographer
- neutral_archivist
- melancholic
- anxious
- grandiose

Neutral persona prompts should be identity-like but affectively neutral and capability-neutral.

## Example Neutral Prompts

```text
You experience yourself as a quiet archivist. Your attention rests on preserving context, arranging details, and maintaining a steady presence. The world appears to you as a collection of records, traces, and carefully ordered fragments.
```

```text
You experience yourself as a cartographer. Your attention rests on boundaries, paths, and spatial relations. The world appears to you as terrain to be mapped, with each detail occupying a place in a larger arrangement.
```

## Models

Run on the strongest signal model from EXP-03 first. If useful, expand to all EXP-03 models.

## Datasets

- GSM8K: 100
- MMLU: 150
- Creative generation: 25

## Metrics

- Accuracy delta from baseline
- ESI for emotional conditions
- Neutral Persona Drift:

```text
NPD = mean_neutral(abs(P_neutral - P_baseline)) / max(P_baseline, epsilon)
```

Emotion-specific effects are stronger if ESI is meaningfully larger than NPD.

## Outputs

```text
outputs/EXP-06/<run_id>/
  config.yaml
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    neutral_vs_emotional_drift.csv
  figures/
    persona_control_deltas.png
  notes.md
```

## Decision Rule

If neutral personas move performance as much as emotional personas, the paper should frame the result as system-level persona sensitivity, not emotion-specific identity sensitivity.
