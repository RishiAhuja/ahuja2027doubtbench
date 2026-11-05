# Using DoubtBench

This guide covers evaluation, task generation, and rebuilding the figures in
the public release. See the [README](README.md) for the paper overview and
[BENCHMARK.md](BENCHMARK.md) for the task and scoring protocol.

## Setup and verification

Use Python 3.10 or later. Run commands from the repository root:

```bash
git clone https://github.com/RishiAhuja/ahuja2027doubtbench.git
cd ahuja2027doubtbench
python scripts/verify_artifact.py
```

The verifier requires only the Python standard library and the included
scorer. It checks task-file hashes, unique identifiers, family and difficulty
counts, gold-answer self-scoring, surface-form pairings, and result-table
coverage. It does not rerun model inference or reconstruct the reported
statistics from raw generations.

Install inference dependencies in an isolated environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Inference loads a Hugging Face causal language model and tokenizer. Use a
machine with enough memory for the selected checkpoint; lower `--batch-size`
if necessary. Model access and downloading are handled by Hugging Face.

## Evaluate the released tasks

The main benchmark contains four task sets: `task_set_16061`,
`task_set_16101`, `task_set_16102`, and `task_set_19003`. Each has 1,600 tasks
and a companion manifest in [`data/`](data/).

```bash
python run_factorial.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --data-file data/task_set_16061.jsonl \
  --out outputs/qwen_task_set_16061 \
  --max-new-tokens 768 \
  --batch-size 8
```

This produces 16,000 responses: five conditions × two contexts × 1,600
tasks. Repeat with the other three task files and a separate output directory
for each. The main benchmark totals 64,000 responses per checkpoint.

For the surface-form analysis, use `--data-file data/surface_forms.jsonl`
and a new output directory. This evaluates 990 renderings of 330 latent tasks,
producing 9,900 responses per checkpoint. The canonical renderings are also
present in `task_set_19003`; account for that overlap when combining analyses.

The evaluator uses greedy decoding, left-padded inputs, and the tokenizer's
chat template when available. CUDA inference uses bfloat16. The model loader
uses automatic device placement. The example explicitly sets a 768-token
output limit; the CLI default is 384. Keep settings fixed across conditions
when making paired comparisons.

### Options and resuming

Run `python run_factorial.py --help` for all flags. Common options are:

| Option | Purpose |
| --- | --- |
| `--conditions` | Comma-separated condition IDs from [BENCHMARK.md](BENCHMARK.md#controlled-prompt-conditions); defaults to all five |
| `--templates` | `minimal`, `reasoning_requested`, or both separated by a comma; defaults to both |
| `--cache-dir` | Location for downloaded model files |
| `--thinking-mode` | `auto` leaves the chat template unchanged; `on` and `off` pass `enable_thinking` to a template that supports it |
| `--bootstrap-resamples` | Number of paired bootstrap replicates; defaults to 3,000 |
| `--bootstrap-seed` | Seed for paired bootstrap intervals; defaults to 18001 |
| `--resume` | Read existing raw records and skip completed task–condition–context cells |

To resume, rerun the same command with `--resume`, keeping the model, task
file, design, and generation settings unchanged. The runner identifies
completed cells by task ID, condition, and context; it does not validate that
the previous run used the same model or settings. Without `--resume`, it
refuses to append to an existing `raw_outputs.jsonl`.

### Output files

Each output directory contains:

| File | Contents |
| --- | --- |
| `config.json` | Model and tokenizer metadata, prompts, generation settings, and run configuration |
| `samples.jsonl` | The tasks supplied to this run |
| `raw_outputs.jsonl` | Records appended after each generated batch, including messages, raw text, scores, token counts, and diagnostics |
| `parsed_outputs.jsonl` | Completed run records sorted by model, context, task ID, and condition |
| `metrics.json` | Accuracy summaries and paired contrasts |
| `tables/by_model_template_condition.csv` | Accuracy, parse-failure rate, truncation rate, and mean generated length per cell |
| `tables/paired_contrasts.csv` | Paired accuracy differences, pair counts, and 95% bootstrap intervals |

The runner writes summaries before checking completeness and diagnostic
thresholds. Exit code `0` means all expected records are present and both
parse-failure and truncation rates are within their limits. Exit code `3`
means one of those checks failed. Each rate limit defaults to 0.02 and can
be set with `--max-parse-failure-rate` and `--max-truncation-rate`.

Run-level summaries describe the supplied file. The paper's
[result tables](results/README.md) aggregate the four released task sets and
use stratified paired bootstrap intervals, as described in the
[supplement](supplementary/supplement.pdf).

## Generate new task sets

The included JSONL files and manifests define the released benchmark. Use
those files to compare with the paper. These commands generate new instances
deterministically from a task-set name and seed:

```bash
python generate_task_set.py \
  --split-id replication_24001 \
  --seed 24001 \
  --families all \
  --per-family 200 \
  --out data/replication_24001.jsonl
```

Each family uses its own derived random stream. The command writes 1,600
tasks and a companion `.manifest.json` file containing counts, seeds, and a
SHA-256 hash. Run `python generate_task_set.py --help` for options.

Create structured and scenario variants of a fixed sample from that set:

```bash
python generate_surface_forms.py \
  --source data/replication_24001.jsonl \
  --out data/replication_24001_surface_variants.jsonl
```

The surface generator selects ten tasks per type with a 4/4/2
easy–medium–hard allocation. For a complete 33-type task set, it writes
**660 additional variants** for 330 source tasks, plus a manifest. Canonical
rows remain in the source file. Each variant retains the source gold answer
and answer type, and records `source_task_id` and `surface_variant` in its
`metadata.doubtbench` object.

## Recreate figures and the appendix

The figure script reads the included CSV files and writes the five figures
to [`figures/`](figures/) in SVG, PDF, and PNG formats:

```bash
python scripts/make_results_figures.py
```

It uses the Python standard library to draw SVGs and requires `rsvg-convert`
on `PATH` for PDF and PNG conversion. The script rebuilds figures from the
reported tables; it does not recompute those tables from model responses.

See [supplementary/README.md](supplementary/README.md) to compile the appendix.
