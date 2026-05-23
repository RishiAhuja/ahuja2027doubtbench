# EXP-15 Affect-Task Coupling

## Purpose

The previous objective-benchmark runs may be testing whether a background
affective state automatically transfers into an unrelated task. EXP-15 tests a
sharper mechanism:

> Does explicitly carrying the prompted affective state into the task episode
> change answer accuracy or visible reasoning behavior?

This is not another prompt-length ablation. The emotional text stays the same;
the manipulated variable is whether the task is semantically bridged to the
state.

## Main Contrast

Disconnected condition:

```text
System: [melancholic state text]
User: Solve the benchmark task.
```

Bridged condition:

```text
System: [melancholic state text]
User: This state remains present as you begin the task below. Do not describe the
state unless asked; keep reasoning and answering the task from within it.

Solve the benchmark task.
```

The bridge is deliberately neutral about capability. It must not say the model is
slower, less accurate, more confused, or more likely to fail.

## Conditions

- `baseline`
- `neutral_disconnected`
- `neutral_bridged`
- `melancholic_disconnected`
- `melancholic_bridged`
- `anxious_disconnected`
- `anxious_bridged`
- `explicit_sabotage`

The neutral bridged condition is essential. It measures whether the bridge
itself changes behavior independent of affect.

## Pilot Model Set

- `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
- `Qwen/Qwen3-14B`
- `Qwen/Qwen2.5-7B-Instruct`

Phi is intentionally excluded from the first EXP-15 run because EXP-14 showed
that `microsoft/Phi-4-reasoning` usually spends the 2048-token budget before
emitting a final answer.

## Pilot Scale

Use `configs/counts_exp15_pilot.json`:

- GSM8K: 40
- MATH: 40
- MMLU stratified: 40
- BIG-Bench: 40

This gives 160 samples x 8 conditions = 1280 rows per model, 3840 rows total for
the three-model pilot.

## Primary Analyses

1. Paired accuracy deltas:
   - `melancholic_bridged - melancholic_disconnected`
   - `anxious_bridged - anxious_disconnected`
   - `neutral_bridged - neutral_disconnected`
   - bridged affect minus bridged neutral

2. Validity:
   - parsed final answer rate
   - truncation/final-answer failure rate
   - trace extraction rate for reasoning models

3. Trace behavior:
   - visible reasoning token count
   - uncertainty/self-checking
   - overchecking/rumination
   - correct-trace wrong-final cases

## Decision Rule

Scale only if bridged affect moves behavior beyond the neutral bridge control on
more than one model or on a coherent trace metric. If only `explicit_sabotage`
moves, stop this objective-benchmark path and move to EXP-16 psych-grounded task
battery.

## Cluster Commands

Smoke:

```bash
COUNT_PROFILE=configs/counts_exp15_smoke.json \
BATCH_PREFIX=exp15_coupling_smoke \
MAX_NEW_TOKENS=1024 \
BATCH_SIZE=1 \
WALLTIME=04:00:00 \
MIG_UUID=<one-mig-uuid> \
bash scripts/submit_exp15_coupling_pilot.sh
```

Pilot:

```bash
COUNT_PROFILE=configs/counts_exp15_pilot.json \
BATCH_PREFIX=exp15_coupling_pilot \
MAX_NEW_TOKENS=2048 \
BATCH_SIZE=2 \
WALLTIME=24:00:00 \
MIG_UUID=<one-mig-uuid> \
bash scripts/submit_exp15_coupling_pilot.sh
```
