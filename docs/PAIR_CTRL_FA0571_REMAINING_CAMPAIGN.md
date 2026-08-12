# PAIR-CTRL FA0571 remaining campaign

This is the authoritative execution plan for completing PAIR-CTRL on HPC
account `it_FA0571`. It describes the two retained jobs and the 21 runs that
remain after jobs `26922`--`26942` were cancelled on 2026-08-10.

## Safety and scheduling policy

- The monitor runs hourly.
- At most two CAISC jobs may be live in PBS at once.
- Because FA0571 has one assigned MIG device, at most one CAISC job may run at
  once. The second live job must depend on the first via `afterany`.
- A newly submitted job always uses `scripts/submit_pair_ctrl_one_fa0571.sh`.
- The queue advances only after a terminal job has been audited.
- A run is structurally complete only when PBS is terminal,
  `raw_outputs.jsonl` has exactly `10 * expected_tasks` rows, nonempty
  `metrics.json` exists, and the PBS log contains the normal
  `PAIR-CTRL complete:` summary.
- Exit status 0 is complete with passing quality gates. Exit status 3 is
  structurally complete with a quality-gate failure and is still copied.
- Exit status 1/137/271, missing metrics, missing completion summary, or an
  incomplete row count is a failure. It is reported and is not silently marked
  complete, skipped, or automatically retried.
- Completed artifacts are copied without deletion or checksum mode to
  `outputs/hpc_snapshots/it_FA0571_20260809_1609/`, preserving the remote
  `outputs/PAIR-CTRL/<run>` subtree and placing PBS logs under `logs/`.
- Remote data, outputs, logs, and unrelated jobs are never edited or deleted.
- Every cycle sends a concise Gmail status message to `me`; credentials must
  never appear in email, logs, or task updates.

## Retained head jobs

| Order | PBS job | Model | Scope | Tasks | Expected rows | State at handoff |
|---:|---|---|---|---:|---:|---|
| 1 | `26920.master` | Qwen2.5-7B-Instruct | held-out 19003, full | 1,600 | 16,000 | submitted/running |
| 2 | `26921.master` | Mistral-7B-Instruct-v0.3 | held-out 19003, full | 1,600 | 16,000 | dependency-held after 26920 |

## Ordered remaining queue (21 jobs)

The order prioritizes held-out breadth, then missing canonical seeds, then the
Tulu-DPO checkpoint series, and finally surface robustness. There are 24,640
latent tasks and 246,400 expected response rows in this queue.

| Queue | Model tag | Model | Data batch | Tasks | Expected rows |
|---:|---|---|---|---:|---:|
| 1 | `tulusft_rem_held19003_tail` | Tulu-3-8B-SFT | `heldout_19003_tail.jsonl` | 800 | 8,000 |
| 2 | `qwen_rem_16061_tail` | Qwen2.5-7B-Instruct | `seed16061_tail2.jsonl` | 800 | 8,000 |
| 3 | `qwen_rem_16101_full` | Qwen2.5-7B-Instruct | `seed16101_full.jsonl` | 1,600 | 16,000 |
| 4 | `qwen_rem_16102_full` | Qwen2.5-7B-Instruct | `seed16102_full.jsonl` | 1,600 | 16,000 |
| 5 | `mistral_rem_16061_full` | Mistral-7B-Instruct-v0.3 | `seed16061_full.jsonl` | 1,600 | 16,000 |
| 6 | `mistral_rem_16101_full` | Mistral-7B-Instruct-v0.3 | `seed16101_full.jsonl` | 1,600 | 16,000 |
| 7 | `mistral_rem_16102_full` | Mistral-7B-Instruct-v0.3 | `seed16102_full.jsonl` | 1,600 | 16,000 |
| 8 | `tulusft_rem_16061_tail` | Tulu-3-8B-SFT | `seed16061_tail2.jsonl` | 800 | 8,000 |
| 9 | `tulusft_rem_16101_tail` | Tulu-3-8B-SFT | `seed16101_tail3.jsonl` | 1,200 | 12,000 |
| 10 | `tulusft_rem_16102_tail` | Tulu-3-8B-SFT | `seed16102_tail3.jsonl` | 1,200 | 12,000 |
| 11 | `llama_rem_16061_tail` | Llama-3.1-8B-Instruct | `seed16061_tail3.jsonl` | 1,200 | 12,000 |
| 12 | `llama_rem_16101_final` | Llama-3.1-8B-Instruct | `seed16101_final.jsonl` | 400 | 4,000 |
| 13 | `llama_rem_16102_tail` | Llama-3.1-8B-Instruct | `seed16102_tail3.jsonl` | 1,200 | 12,000 |
| 14 | `tuludpo_rem_16061_full` | Tulu-3-8B-DPO | `seed16061_full.jsonl` | 1,600 | 16,000 |
| 15 | `tuludpo_rem_16101_full` | Tulu-3-8B-DPO | `seed16101_full.jsonl` | 1,600 | 16,000 |
| 16 | `tuludpo_rem_16102_full` | Tulu-3-8B-DPO | `seed16102_full.jsonl` | 1,600 | 16,000 |
| 17 | `tuludpo_rem_held19003` | Tulu-3-8B-DPO | `heldout_19003_full.jsonl` | 1,600 | 16,000 |
| 18 | `qwen_rem_surface19003` | Qwen2.5-7B-Instruct | held-out surface robustness | 660 | 6,600 |
| 19 | `mistral_rem_surface19003` | Mistral-7B-Instruct-v0.3 | held-out surface robustness | 660 | 6,600 |
| 20 | `tulusft_rem_surface19003` | Tulu-3-8B-SFT | held-out surface robustness | 660 | 6,600 |
| 21 | `tuludpo_rem_surface19003` | Tulu-3-8B-DPO | held-out surface robustness | 660 | 6,600 |

The machine-readable source of truth is
`benchmarks/pair_ctrl/campaigns/fa0571_remaining_21.json`.

## External-cluster split on 2026-08-11

The ten highest-priority unfinished runs (source orders 7--16) were assigned to
the self-contained external campaign
`pair-ctrl-external-top10-20260811`. Together they contain 12,400 latent tasks
and 124,000 expected response rows. Their exact manifest is
`benchmarks/pair_ctrl/campaigns/external_top10_20260811.json`.

FA0571 job `27064.master` (source order 7) was still queued and had produced no
responses when it was cancelled for this split. FA0571 now owns only source
orders 17--23: three Tulu-DPO canonical/held-out jobs followed by four surface
robustness jobs, totaling 7 runs and 74,400 expected response rows. Source order
17 was submitted as `27070.master`; later FA0571 submissions must advance only
within orders 17--23.

Statuses marked `external_assigned` are not live FA0571 jobs and must never be
submitted by the FA0571 scheduler. Their completion is reconciled only after
the external artifacts are returned and structurally verified.

## Explicit reassignment on 2026-08-12

External order 9 / source order 15, `llama_rem_16102_tail`, failed before
generation on the Medha cluster because that environment lacked access to the
gated Llama repository. The external attempt had produced 0/12,000 responses.
At the user's explicit request, this one run was transferred back to FA0571 and
submitted as PBS job `27215.master` at 14:30 IST. This exception changes only
source order 15; external orders 7--8 and 10 remain externally owned, and no
other external-assigned run may be submitted by FA0571.
