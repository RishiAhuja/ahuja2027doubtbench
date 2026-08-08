# EXP-18 Common-Prefix Factorial

## Purpose

Resolve the paper's main identification gap: whether the apparent benefit of a
compound self-evaluation prompt comes from self-doubt, from its explicit checking
instruction, or from visible reasoning already requested by the task.

## Fixed design

- Shared helpful-assistant prefix in every condition.
- Six open checkpoints: Qwen2.5-7B-Instruct, Mistral-7B-Instruct-v0.3,
  Llama-3.1-8B-Instruct, Tulu-3-8B-SFT, Tulu-3-8B-DPO, and
  Phi-3.5-mini-instruct.
- Three independent seeds of 400 shared EXP-16 working-memory and inhibition
  tasks (1,200 paired items in total).
- Two task templates: minimal final-answer formatting and an explicit request to
  show intermediate steps.
- Five conditions: neutral, pure self-doubt without checking verbs, direct
  checking, self-doubt plus checking, and checking plus forced concision.
- Greedy decoding and paired item-level analysis.
- 3,000 paired bootstrap resamples for each pre-specified contrast.

Each seed requires 4,000 generations per checkpoint. The complete three-seed
campaign is 12,000 generations per checkpoint and 72,000 generations across six
checkpoints. The set spans four foundation families; the two Tulu checkpoints
are a controlled post-training comparison on the same Llama-3.1 backbone, not
independent model-family replications.

## Primary contrasts

1. Pure self-doubt minus neutral.
2. Direct checking minus neutral.
3. Self-doubt plus checking minus direct checking.
4. Self-doubt plus checking minus pure self-doubt.
5. Checking plus concision minus checking.
6. Each contrast under minimal versus already-reasoning-eliciting task prompts.

## Cluster launch

Run a smoke test before a full model run. The PBS job requires exactly one MIG UUID.

```bash
qsub \
  -v MIG_UUID=<single-mig-uuid>,MODEL=Qwen/Qwen2.5-7B-Instruct,MODEL_TAG=qwen25_smoke,DATA_FILE=experiments/data/exp16_self_doubt_focus_smoke.jsonl,MAX_NEW_TOKENS=384,BATCH_SIZE=8 \
  -o logs/exp18_qwen25_smoke.log \
  scripts/pbs_exp18_factorial.pbs
```

After validating row counts, parsing, truncation, and condition balance, use the
400-task pilot file for the full job.

## Stop conditions

Do not interpret or extend the run if:

- the smoke job does not produce 200 rows;
- any condition is missing shared task IDs;
- parse failures exceed 2 percent;
- truncation exceeds 2 percent;
- the common prefix differs across conditions;
- the model revision or task file is not recorded in `config.json`.

The runner enforces row integrity and global parse/truncation thresholds before
returning success, so a PBS `afterok` dependency cannot launch a full run after a
failed smoke-quality check.

## Current PBS campaign (2026-08-08)

- `26383.master`: Qwen2.5 smoke, completed with 200/200 unique rows, zero parse
  failures, and zero truncations.
- `26384.master`: Qwen2.5 full 4,000-generation run.
- `26385.master`: Mistral-7B smoke, dependent on successful Qwen completion.
- `26386.master`: Mistral-7B full run, dependent on a successful smoke exit.

The current account has no Hugging Face token for gated Llama weights, so no
Llama job was knowingly scheduled to fail. A Llama replication remains desirable
after authorized model access is configured.

The first Mistral smoke (`26385.master`) timed out before model loading because
the Hugging Face Xet client stalled on `tokenizer.model`. The retry path disables
Xet, downloads the snapshot through `cpuq`, and only then allocates a GPU for the
smoke and full runs.

The corrected download (`26396.master`) and smoke (`26397.master`) completed
successfully. The replacement full run is `26398.master`.

### Revised two-account split

The core workload is divided three checkpoints per account on distinct MIG slices:

| Account | Model | Smoke | Full | Status / policy |
|---|---|---:|---:|---|
| `it_FA0618` | Qwen2.5-7B-Instruct | `26383` | `26384` | Complete |
| `it_FA0618` | Mistral-7B-Instruct-v0.3 | `26397` | `26398` | Smoke passed; full running |
| `it_FA0618` | Tulu-3-8B-DPO | `26420` | `26421` | Runs after model download `26419` and Mistral |
| `it_FA0571` | Llama-3.1-8B-Instruct | `26402` | `26403` | Smoke passed; full running |
| `it_FA0571` | Tulu-3-8B-SFT | `26405` | `26406` | Runs after Llama |
| `it_FA0571` | Phi-3.5-mini-instruct | `26422` | `26423` | Runs after Tulu-SFT; full only after quality smoke |

This is six checkpoints across four foundation families: Qwen, Mistral,
Llama/Tulu, and Phi. Tulu-SFT and Tulu-DPO are deliberately retained as a
controlled post-training comparison on the same Llama-3.1 backbone; they must be
reported as checkpoints, not as two independent model families.

The earlier held Qwen3 and DeepSeek jobs (`26407`--`26412`) were cancelled before
execution when the workload was rebalanced and the independent Phi family was
selected for the sixth core slot. Phi-4-reasoning jobs `26417`/`26418` were also
cancelled before execution: prior project runs show that checkpoint repeatedly
exhausting a 2,048-token reasoning budget before a usable final answer. The
ordinary instruction-tuned Phi-3.5 checkpoint preserves family breadth without
introducing that known truncation confound.

### Independent task-seed replications

Two further seeds reuse the frozen factorial, decoding, parser, and quality
thresholds. They are serialized behind the initial seed on each account, so a
failed upstream quality gate prevents downstream use of that account's results.

| Account | Model | Seed 16101 | Seed 16102 |
|---|---|---:|---:|
| `it_FA0618` | Qwen2.5-7B-Instruct | `26424` | `26425` |
| `it_FA0618` | Mistral-7B-Instruct-v0.3 | `26426` | `26427` |
| `it_FA0618` | Tulu-3-8B-DPO | `26428` | `26429` |
| `it_FA0571` | Llama-3.1-8B-Instruct | `26430` | `26431` |
| `it_FA0571` | Tulu-3-8B-SFT | `26432` | `26433` |
| `it_FA0571` | Phi-3.5-mini-instruct | `26434` | `26435` |

These are confirmatory task-generator replications, not new exploratory
experiment families. The paper should pool them only after reporting per-seed
effects and verifying that qualitative conclusions agree across seeds.
