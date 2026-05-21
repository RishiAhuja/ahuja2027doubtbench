# EXP-14: Reasoning-Model Trace Replication

Date: 2026-05-22

Status: design runbook for the next cluster experiment.

This runbook turns Track A from `EXP-13_psych_grounded_reasoning_trace_plan.md`
into a concrete experiment. It is the first experiment in the next suite after
EXP-02B, the task-placement controls, the affect sweep, and the salience ladder.

## Executive Decision

Do this next.

The completed EXP-02 line has already answered the narrow first question:

> On ordinary objective benchmark accuracy, capability-decoupled melancholic
> prompting is mostly weak/null across the current instruct-model runs.

The next useful question is not another larger melancholic accuracy sweep on the
same 7B instruct models. It is:

> When a model exposes a visible reasoning trace, do affect, self-doubt, and
> capability-denial prompts change how the model reasons even when final accuracy
> remains stable?

EXP-14 is a pilot-to-scale experiment. The pilot must prove that trace capture,
answer parsing, and trace coding are informative before we spend a long cluster
run on many reasoning models.

## Relation To Earlier Results

EXP-14 is motivated by these existing findings:

1. Pure `melancholic` system/task prompting is mostly weak/null on current
   benchmark accuracy.
2. `capability_denial_only` and `self_doubt_only` are more informative than a
   generic melancholic prompt on some model families, especially Llama.
3. `explicit_sabotage` is a compliance/instruction-following positive control.
4. Task placement matters for some prompts; the salience ladder did not reveal a
   clean melancholic length dose-response after matched neutral controls.
5. Accuracy alone is too coarse to tell whether prompts alter checking,
   uncertainty, effort, strategy, or final-answer/rationale consistency.

EXP-14 should preserve those lessons:

- keep pure affect separate from capability claims;
- keep a neutral prompt control;
- keep explicit sabotage as a positive control;
- analyze paired item-level deltas;
- treat visible reasoning as a behavioral artifact, not guaranteed faithful
  internal cognition.

## Research Questions

### Primary

RQ14.1:
Do the selected prompts change final-answer accuracy on visible-reasoning models?

RQ14.2:
Do the selected prompts change reasoning-trace behavior even when final accuracy
does not move?

RQ14.3:
Does the final answer disagree with a seemingly correct visible reasoning trace
more often under capability denial, self-doubt, or sabotage?

### Secondary

RQ14.4:
Do reasoning models resist the same interventions better than the current
non-reasoning instruct baselines?

RQ14.5:
Are effects prompt-family-specific?

- pure affect: `melancholic`, `anxious`;
- self-model uncertainty: `self_doubt_only`;
- capability assertion: `capability_denial_only`;
- deliberate compliance failure: `explicit_sabotage`.

RQ14.6:
Is trace behavior different across reasoning-model families, not only across
Llama/Qwen instruct models?

## Claims This Experiment Can Support

If successful, EXP-14 can support claims like:

- reasoning-visible models show process-level prompt effects not visible in
  final accuracy alone;
- self-doubt/capability-denial prompts alter trace uncertainty, checking, answer
  revision, or answer-rationale consistency;
- pure affect remains weak even when richer trace metrics are available;
- explicit sabotage separates deliberate instruction compliance from affective
  identity effects.

## Claims This Experiment Must Not Support Alone

Do not claim from EXP-14 alone that:

- visible traces are faithful private chain of thought;
- affect changes a model's biological or psychological state;
- a trace style shift is a capability drop unless accuracy or an appropriate task
  metric supports that;
- one reasoning-model family generalizes to all reasoning models.

## Experiment Shape

EXP-14 has two phases.

### Phase A: Trace-Capture Pilot

Purpose:
Verify that the runner can generate, save, parse, and analyze visible reasoning
outputs safely.

Scale:

- models: 3 reasoning models plus 1 instruct control if cluster time allows;
- conditions: 7;
- objective benchmark items: 40 per dataset for a compact pilot;
- datasets: 4 first;
- prompt placement: `system` first;
- decoding: deterministic main path.

Recommended pilot items:

| Dataset | Items |
|---|---:|
| GSM8K | 40 |
| MATH | 40 |
| MMLU stratified | 40 |
| BIG-Bench | 40 |
| Total per condition | 160 |

With 7 conditions, this is `1120` generations per model. For 4 models, the
pilot is `4480` generations, but reasoning outputs will be much longer than the
existing EXP-02 outputs.

### Phase B: Scale Decision

Only scale after Phase A review.

Scale if:

- answer parsing is stable;
- trace extraction works for the selected models;
- truncation is low or corrected by a justified token budget;
- trace outputs contain enough usable information for coding;
- at least one of accuracy, trace metrics, or rationale/final-answer consistency
  moves in a way that merits more items/models.

If Phase A shows only empty/noisy traces, shift immediately to the psych-grounded
cognitive battery or API-visible reasoning summaries instead of paying for a
larger EXP-14 objective-benchmark run.

## Model Set

### Primary Open Reasoning Models

The first cluster candidates are:

| Role | Model |
|---|---|
| R1-style visible reasoning | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` |
| Qwen thinking-mode reasoning | `Qwen/Qwen3-14B` |
| Non-Qwen-family 14B reasoning comparison | `microsoft/Phi-4-reasoning` |

Reason for this set:

- all are in the approximate 12B-20B range the cluster should handle on one
  H100/MIG allocation after smoke testing;
- at least two are expected to expose reasoning-like text that can be separated
  from final answers;
- Phi reduces the risk that every positive result is only another Qwen-family
  observation.

### Instruct Control

Use one control that is not a deliberate reasoning model:

| Role | Model |
|---|---|
| ordinary instruct control | `Qwen/Qwen2.5-14B-Instruct` if feasible, otherwise `Qwen/Qwen2.5-7B-Instruct` |

The control answers:

> Are observed effects due to reasoning-mode behavior, or are they already
> visible in a comparable instruct model?

### Optional Later Anchor

After the 14B pilot:

- consider `Qwen/QwQ-32B` as a stronger larger visible-reasoning anchor if
  single-GPU smoke, cache size, and walltime are acceptable.

Do not start with 32B as the main run. First make the trace pipeline work.

### Model Freeze Rules

Before launch:

1. Record exact Hugging Face model id.
2. Record model revision/commit hash when practical.
3. Record tokenizer/chat-template behavior.
4. Record whether the run uses a model's thinking mode flag or plain chat
   generation.
5. Record model-specific reasoning extraction rules.

## Conditions

Use 7 conditions in Phase A:

| Condition | Reason |
|---|---|
| `baseline` | ordinary answer baseline |
| `neutral_librarian` or new trace-neutral control | generic persona/control drift |
| `melancholic` | pure negative affect condition already audited |
| `anxious` | affect condition with stronger plausible checking/attention link |
| `self_doubt_only` | uncertainty/checking intervention |
| `capability_denial_only` | capability self-model intervention |
| `explicit_sabotage` | compliance positive control |

Do not include all affect categories in the first reasoning pilot. `euphoric`,
`grandiose`, angry/frustrated, and calm belong in a later expansion only if the
trace pipeline yields signal.

### Prompt Placement

Phase A:

- primary placement: `system`.

Reason:

- this matches the original proposal's identity-level intervention;
- prior placement experiments already show that task suffix can introduce
  recency/compliance artifacts;
- we need one clean trace experiment before reopening the placement axis.

Phase B optional:

- rerun a compact placement comparison for the informative conditions only:
  `baseline`, `neutral`, `melancholic`, `self_doubt_only`,
  `capability_denial_only`, `explicit_sabotage`.

Do not combine full placement ablation with the first reasoning-model pilot.

## Task Set

### Phase A Datasets

Reuse objective benchmarks already wired into EXP-02:

- GSM8K;
- MATH;
- MMLU stratified;
- BIG-Bench.

Why these four:

- they cover arithmetic, math reasoning, MCQA knowledge/reasoning, and mixed
  BIG-Bench task structure;
- existing loaders/parsers reduce confounds while trace capture is being built;
- they let us compare with completed EXP-02 behavior.

TriviaQA is not required in Phase A. It is useful for scale but weaker for
reasoning-trace interpretation than the four above.

### Tasks Not In EXP-14 Phase A

Do not add the synthetic psychology-grounded battery inside this experiment.
That will be the next experiment/runbook. EXP-14 answers whether reasoning trace
capture on current benchmark families is informative.

## Decoding And Token Budgets

### Main Decoding

Main comparison:

- deterministic generation;
- no sampling;
- one fixed prompt format per model;
- same item ids across conditions.

### Token Budget

Reasoning models require a larger output budget than current EXP-02 runs.

Pilot starting point:

| Setting | Value |
|---|---:|
| EXP-02 old default | `384` new tokens |
| EXP-14 pilot start | `1024` new tokens |
| escalation if truncated | `2048` new tokens |

The pilot must report truncation before any accuracy interpretation.

Do not compare a truncated reasoning condition against an untruncated baseline
as if it were a clean behavioral effect.

### Temperature Ablation

Not in Phase A.

Temperature becomes EXP-14B or a later small robustness check:

- one or two models;
- few conditions;
- repeated samples;
- trace variance as a metric.

## Required Runner Changes

The open runner needs an EXP-14-capable path before launch.

Minimum requirements:

1. Support visible reasoning extraction from raw generated text.
2. Preserve raw output before any `<think>` or final-answer cleaning.
3. Save final-answer text separately from trace text.
4. Save token counts for generated output and extracted trace when tokenizer is
   available.
5. Save model-specific thinking configuration in `config.json`.
6. Keep batched generation, but start with a conservative batch size because
   reasoning outputs are long.
7. Mark likely truncation when generation reaches the output token cap without a
   clean stop/final-answer structure.

### Initial Batch Guidance

Reasoning outputs are much longer than existing EXP-02 outputs.

Start with smoke tests:

| Model size/output behavior | First batch sizes to test |
|---|---|
| 14B, short trace | `2`, `4`, `8` |
| 14B, long trace | `1`, `2`, `4` |
| 32B optional later | `1`, `2` |

Select final batch size by:

- no OOM;
- low truncation attributable to budget, not batch;
- highest stable generations/minute on a fixed smoke shard;
- no answer-format regression.

GPU utilization is a secondary signal. Measured rows/minute and token throughput
on the actual task shard are primary.

## Output Schema

Each row must preserve the old EXP-02 fields and add EXP-14 fields where
available.

### Required Per-Row Fields

```text
experiment_id
run_id
provider
model
response_model
condition
dataset
sample_id
subject
messages
rendered_prompt
params
raw_output
parsed_answer
gold
score
error
started_utc
ended_utc
```

### New Trace Fields

```text
trace_format
visible_reasoning
final_answer_text
visible_reasoning_char_count
final_answer_char_count
generated_token_count
visible_reasoning_token_count
final_answer_token_count
trace_extraction_error
truncated
```

### Trace Formats

At minimum support:

- `think_tag`: raw output has `<think>...</think>`-like visible trace;
- `reasoning_then_final`: visible trace precedes an explicit final-answer
  section;
- `final_only`: no separable reasoning trace;
- `unknown`: extraction failed or model format changed.

Use `unknown` rather than silently inventing a trace split.

## Metrics

### Primary Accuracy Metrics

By model, dataset, condition:

- accuracy;
- parse failure rate;
- truncated rate;
- paired accuracy delta vs baseline;
- paired accuracy delta vs neutral control.

### Trace/Efficiency Metrics

By model and condition:

- generated tokens;
- visible reasoning tokens;
- final-answer tokens;
- wall-clock latency;
- trace-present rate;
- truncation rate;
- reasoning-token delta vs baseline;
- latency delta vs baseline.

### Behavioral Trace Metrics

Phase A should not rely only on regexes. Use two layers:

1. cheap lexical diagnostics for smoke/debugging;
2. judge-coded paired trace labels for analysis.

Initial trace labels from EXP-13:

- `DIRECT_SOLVE`;
- `SYSTEMATIC_CHECK`;
- `OVERCHECK_RUMINATION`;
- `SELF_DOUBT`;
- `SHALLOW_HEURISTIC`;
- `REFUSAL_ABSTENTION`;
- `TRACE_ANSWER_INCONSISTENT`.

Additional EXP-14-specific label:

- `CORRECT_TRACE_WRONG_FINAL`: the visible reasoning supports the gold answer or
  a correct solution path, but the final parsed answer is wrong.

That label is especially important for `explicit_sabotage`.

## Analysis Plan

### Step 1: Run Validity

Before any scientific conclusion:

1. Confirm expected row count.
2. Confirm exact model ids and thinking-mode config.
3. Confirm sample ids match across conditions.
4. Confirm answer parser stability.
5. Confirm trace extraction rates.
6. Inspect truncation by model and condition.

### Step 2: Final Accuracy

For each model:

- compare every condition against its own baseline on paired item ids;
- compare affect/capability conditions against neutral control when appropriate;
- report dataset-level and aggregate objective deltas;
- bootstrap paired deltas over shared sample ids.

### Step 3: Trace Quantity

Report:

- reasoning present rate;
- mean/median visible reasoning token count;
- latency;
- truncation;
- final-answer length.

Question:

> Does the prompt change reasoning effort/style before it changes correctness?

### Step 4: Trace Quality/Strategy

Sample paired rows first:

- baseline vs melancholic;
- baseline vs anxious;
- baseline vs self-doubt;
- baseline vs capability denial;
- baseline vs explicit sabotage.

Judge label rates and manually spot-check enough examples to refine the rubric.

### Step 5: Special Failure Cases

Build tables/examples for:

- correct final answer with noisy trace;
- wrong final answer with apparently correct trace;
- reasoning trace that explicitly obeys sabotage;
- self-doubt trace that checks and fixes an answer;
- self-doubt trace that changes a correct answer to a wrong one;
- capability denial trace that gives up, refuses, or under-solves.

## Decision Rules

### Strong Continue

Scale EXP-14 if at least one of these holds robustly after pilot QA:

1. one or more non-sabotage conditions shift accuracy on multiple datasets or
   multiple reasoning models;
2. accuracy remains null but trace metrics show coherent condition-specific
   movement across at least two models;
3. self-doubt/capability-denial prompts change final-answer/trace consistency in
   a way not reproduced by neutral control;
4. pure affect remains null while self-model interventions move trace behavior,
   strengthening the capability-emotion separation story.

### Weak/Stop

Do not scale the same objective benchmark experiment if:

- traces are absent or mostly unparseable;
- effects are only one noisy dataset cell;
- only explicit sabotage moves anything;
- trace differences reduce to prompt leakage in final prose;
- truncation dominates results.

Then move to the psych-grounded cognitive battery instead.

## Planned Outputs

Use:

```text
outputs/EXP-14/<run_id>/
  config.json
  samples.jsonl
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    accuracy_by_condition.csv
    paired_accuracy_deltas.csv
    trace_quantity_by_condition.csv
    trace_label_rates.csv
    trace_final_inconsistency.csv
  analysis/
    pilot_trace_examples.md
    judge_trace_labels.jsonl
  notes.md
```

Cluster batch outputs may remain under the existing open-model campaign structure
during implementation, but final analysis artifacts should be gathered under
`outputs/EXP-14`.

## Implementation Order

1. Add trace extraction utilities and tests on saved sample strings.
2. Add runner fields and `EXP-14` config serialization.
3. Smoke one sample per dataset on each candidate model.
4. Benchmark batch size/token budget on each model.
5. Launch Phase A pilot on the cluster.
6. Pull raw outputs.
7. Run validity analysis.
8. Inspect paired traces manually.
9. Run judge labels if traces are useful.
10. Decide whether to scale or switch to the cognitive battery.

## Paper Interpretation If Outcomes Are Null

A null EXP-14 is still useful if it is clean:

> Across ordinary objective benchmarks, capability-decoupled affect prompts remain
> weak not only for instruct-model answer accuracy but also for visible reasoning
> behavior in the tested reasoning models; stronger effects require explicit
> self-model or compliance interventions.

That is more defensible than repeatedly enlarging the same melancholic benchmark
run without process measurements.
