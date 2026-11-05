# DoubtBench

DoubtBench is a controlled exact-answer benchmark for measuring whether
self-doubt wording changes language-model accuracy beyond a direct instruction
to check the work. This repository is the public release for *DoubtBench:
Does Self-Doubt Help Language Models—or Just Make Them Check?* (WSDM
Findings 2027). It contains the tasks, the factorial evaluator and
exact-answer scorer, the reported result tables and figures, and the
supplementary appendix.

## Contents

- `data/`: four independently generated task sets of 1,600 tasks
  (`task_set_16061`, `task_set_16101`, `task_set_16102`, and
  `task_set_19003`) and the paired surface-form file `surface_forms.jsonl`.
- `run_factorial.py`: command-line entry point for the five-condition by
  two-context evaluation.
- `generate_task_set.py` and `generate_surface_forms.py`: deterministic task
  and answer-preserving surface-form generators.
- `doubtbench/`: task generators and the exact-answer scorer.
- `evaluation/`: Hugging Face runner, generation helpers, and the factorial
  design.
- `core/`: shared I/O helpers.
- `results/`: checkpoint, condition, task-set, family, difficulty,
  surface-form, and post-training summaries.
- `figures/`: the five result figures.
- `scripts/make_results_figures.py`: deterministic figure generation from the
  result tables.
- `scripts/verify_artifact.py`: structural and numerical integrity checks.
- `supplementary/`: the appendix (`supplement.tex`), together with its tables
  and figures.
- `BENCHMARK.md`: families, prompt conditions, task contexts, scoring, and
  the Conditional Doubt Effect.

Evaluation loads a causal language model at runtime. A factorial run writes
the configuration, sampled tasks, raw responses, parsed responses, aggregate
metrics, and CSV tables to the requested output directory. The CSV files in
`results/` are the compact statistics reported in the paper.

## Verify

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

## Protocol and appendix

`BENCHMARK.md` specifies the evaluation protocol. Compile the appendix with
the instructions in `supplementary/README.md`.
