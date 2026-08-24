# DoubtBench code, data, and results

This artifact accompanies *DoubtBench: Does Self-Doubt Help Language
Models—or Just Make Them Check?* It contains the benchmark instances, the
factorial evaluator and exact-answer scorer, the compact result tables used in
the paper and supplementary material, and the code used to render the result
figures.

## Contents

- `data/`: four independently generated task sets (1,600 tasks each) and the
  paired surface-form set.
- `run_factorial.py`: the command-line entry point for the full five-condition
  by two-context evaluation.
- `generate_task_set.py` and `generate_surface_forms.py`: deterministic task
  and answer-preserving surface-form generators.
- `doubtbench/`: task generators and exact-answer scorer.
- `evaluation/`: Hugging Face runner, generation helpers, and factorial design.
- `core/`: small shared I/O helpers.
- `results/`: machine-readable checkpoint-, condition-, task-set-, family-,
  difficulty-, surface-, and post-training summaries.
- `figures/`: the five result figures included with the supplementary material.
- `scripts/make_results_figures.py`: deterministic figure-generation code.
- `scripts/verify_artifact.py`: structural and numerical integrity checks.

The archive intentionally omits model weights, caches, scheduler files, logs,
and raw model completions. The included result CSV files are the compact
statistics reported in the paper; the benchmark and evaluator are sufficient
to produce new response records for any compatible causal language model.

## Verify the artifact

Python 3.10 or later is required. The integrity check uses only the standard
library and the included scorer:

```sh
python scripts/verify_artifact.py
```

A successful run reports 6,400 unique main tasks, 330 latent surface tasks,
990 surface renderings, and six evaluated checkpoints in the result tables.

## Install inference dependencies

Create an isolated environment and install:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the factorial evaluation

The following example evaluates one complete task set. Replace the model
repository and batch size as appropriate for the available accelerator.

```sh
python run_factorial.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --data-file data/task_set_16061.jsonl \
  --out outputs/qwen_task_set_16061 \
  --max-new-tokens 768 \
  --batch-size 8
```

The command uses greedy decoding and evaluates every task under five prompt
conditions and two task contexts. It writes the full configuration, sampled
tasks, raw responses, parsed responses, aggregate metrics, and CSV tables to
the requested output directory. Use `--resume` to continue an interrupted run
without regenerating completed task–condition–context cells.

To evaluate the answer-preserving surface forms, pass
`data/surface_forms.jsonl`. This file contains the canonical, structured, and
scenario rendering of each of 330 latent tasks.

## Generate a new task set

The generator derives an independent random stream for each family. This makes
the output deterministic for a given task-set name and seed:

```sh
python generate_task_set.py \
  --split-id replication_24001 \
  --seed 24001 \
  --families all \
  --per-family 200 \
  --out data/replication_24001.jsonl
```

To create the two additional surface forms from a complete task set:

```sh
python generate_surface_forms.py \
  --source data/replication_24001.jsonl \
  --out data/replication_24001_surface_variants.jsonl
```

## Recreate the figures

The figure script reads the included CSV tables and writes SVG, PDF, and PNG
files to `figures/`:

```sh
python scripts/make_results_figures.py
```

It uses only the Python standard library for drawing and the external
`rsvg-convert` command for PDF and PNG conversion.

## Evaluation protocol

See `BENCHMARK.md` for the benchmark composition, exact prompt conditions,
task contexts, outcome definitions, and the Conditional Doubt Effect.
