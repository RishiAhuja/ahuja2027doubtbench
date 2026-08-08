# PAIR-CTRL

**Paired Assessment of Intervention Responses in Cognitive-Control Tasks**

PAIR-CTRL is a paired counterfactual benchmark for measuring how prompt
interventions change language-model execution on deterministic cognitive-control
tasks. Its defining feature is not a leaderboard of raw accuracy. The same task
instance is evaluated under frozen prompt components and task-elicitation
contexts, enabling within-item attribution of behavioral changes.

Status: **v1 design candidate; not yet frozen or released.**

The normative definition is in [BENCHMARK_CARD.md](BENCHMARK_CARD.md). Existing
`EXP-16` and `EXP-18` files are development predecessors. They must not be called
PAIR-CTRL v1 until the manifest, independent validation, splits, and analysis
plan below are frozen.

## Current generated inventory

- Eight cognitive-control families and 33 task types.
- Four seeds with 1,600 base tasks per completed split (200 per family).
- 6,400 base tasks in total.
- Three surface forms per type (canonical, structured, and scenario-framed),
  producing 99 type--surface combinations. The paired held-out robustness layer
  contains 660 variants over 330 latent tasks.
- Five prompt interventions crossed with minimal and reasoning-requested task
  contexts, yielding ten paired cells per task and checkpoint.
- Four representative checkpoints from independent Qwen, Mistral, Llama, and
  Phi foundation families cover all 6,400 tasks. Two additional Tulu
  checkpoints cover 2,400 tasks each from the four-family core and historical
  focused splits as a scoped post-training case study. This
  hierarchical campaign plus the four-model surface-form study contains
  330,400 generations; a fully crossed six-checkpoint core matrix alone would
  contain 384,000.

The three historical seeds combine predecessor working-memory/inhibition tasks
with generated flexibility/rule-learning extensions. Seed 19003 is a candidate
held-out split and remains sealed for confirmatory analysis until validation and
analysis freeze.

## One-sentence purpose

PAIR-CTRL tests whether an apparent benefit from self-doubt language is
attributable to self-doubt itself, to an embedded checking instruction, or to
interaction with reasoning already requested by the task.

## Planned v1 package

```text
benchmarks/pair_ctrl/
  README.md
  BENCHMARK_CARD.md
  RUN_LEDGER.md               # checkpoint/split job provenance
  generate_split.py           # deterministic split generator
  validate_split.py           # structural/hash/self-score validation
  build_combined_split.py     # historical focused split + family extension
  merge_components.py         # normalize all eight families into full splits
  VERSION.json                 # create at design freeze
  manifests/                   # split hashes and inventory
  data/                        # frozen dev/replication/test JSONL
  validation/                  # independent-solvers and audit reports
  analysis/                    # frozen contrasts and result tables
```

The first campaign budget audit is recorded in
`validation/generation_budget_diagnostic.md`. Its 384-token runs are diagnostic
only and are excluded from confirmatory analysis.

## Working paper title

> **Doubt or Check? PAIR-CTRL, a Paired Cognitive-Control Benchmark for
> Deconfounding Metacognitive Prompt Effects**
