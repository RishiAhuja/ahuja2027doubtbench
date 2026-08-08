# PAIR-CTRL run ledger

Updated: 2026-08-08 (Asia/Kolkata)

## FA0618 storage recovery (2026-08-08 19:13 IST)

The Qwen held-out core job `26650` completed with 8,000/8,000 rows and a
metrics file. Job `26651` was interrupted by a full shared `/Data1` filesystem
after 2,128 valid rows; its single torn trailing JSON line was removed after
validation. The old `afterany` chain then failed through the remaining jobs
because PBS could not stage output files.

Approximately 32 GB was recovered by removing only regenerable caches unrelated
to this campaign: Qwen3-VL-8B-Instruct, Phi-4-multimodal-instruct,
MiniCPM-V-4.6, and the pip download cache. Qwen2.5, Mistral, Tulu-DPO, all
experiment outputs, and the Python environment were preserved. The repaired
priority chain is:

| Job | Purpose |
|---:|---|
| 26790 | Resume Qwen held-out breadth in the original `26651` run directory |
| 26791 | Qwen held-out final-breadth extension |
| 26792 | Mistral held-out base |
| 26793 | Mistral held-out breadth extension |
| 26794 | Mistral held-out final-breadth extension |
| 26795 | Qwen held-out surface robustness |
| 26796 | Mistral held-out surface robustness |

At verification, `26790` was running on GPU and had begun appending valid rows.

## Active evidence-priority campaign

Every run crosses five prompt interventions with two task-elicitation contexts.
Because the accounts expire on 2026-08-09 and 2026-08-10, the queue first secures
one complete confirmatory split on all four independent foundation families.
Only then does it run alternate surfaces, procedural-seed replication, and the
within-Llama Tulu case study. Jobs within an account are serialized using
`afterany`, so a failed checkpoint does not silently cancel later models.

The held-out canonical core consists of an 800-task four-family file, a 400-task
monitoring/planning file, and a 400-task relational/goal-management file. Thus
each checkpoint below receives all 1,600 latent held-out tasks and 33 task types.
The surface job adds 660 answer-preserving variants over 330 of those tasks.

| Account | Checkpoint | Held-out base | Held-out monitor/plan | Held-out relation/goal | Surface |
|---|---|---:|---:|---:|---:|
| it_FA0618 | Qwen2.5-7B-Instruct | 26650 | 26651 | 26652 | 26656 |
| it_FA0618 | Mistral-7B-Instruct-v0.3 | 26653 | 26654 | 26655 | 26657 |
| it_FA0571 | Llama-3.1-8B-Instruct | 26687 | 26688 | 26689 | 26693 |
| it_FA0571 | Phi-3.5-mini-instruct | 26690 | 26691 | 26692 | 26694 |

Completion of the first three held-out columns gives the primary four-model
matrix: 6,400 latent model--task evaluations and 64,000 paired generations.
Canonical plus structured and scenario wording gives 99 type--surface
combinations; the surface jobs add 26,400 generations.

## Secondary queued work

- Seed 16061 completion (including 768-token focused reruns): Qwen
  `26658`--`26661`; Mistral `26662`--`26665`; Llama `26695`--`26698`; Phi
  `26699`--`26702`.
- Tulu case study: DPO focused/held-out/extension `26666`--`26668`; SFT
  focused/held-out/extension `26703`--`26705`.
- Seeds 16101 and 16102: Qwen `26669`--`26676`; Mistral `26677`--`26684`;
  Llama `26706`--`26713`; Phi `26714`--`26721`.
- Focused Tulu replications: DPO `26685`--`26686`; SFT `26722`--`26723`.

If all secondary jobs complete, the four independent family representatives
cover all 6,400 latent core tasks across four procedural splits. The two Tulu
checkpoints remain deliberately narrower post-training comparisons and are not
counted as independent model families.

## Foundation-family accounting

The six checkpoints represent four independent foundation families: Qwen,
Mistral, Llama, and Phi. Llama-3.1-Instruct, Tulu-SFT, and Tulu-DPO are three
checkpoints on a shared Llama-family foundation and support a scoped
post-training comparison; they are not counted as three independent families.

Jobs `26436`--`26473` were cancelled after a live throughput audit showed that
their submitted MIG UUIDs were inactive and Transformers had fallen back to
eight-CPU inference. Their partial outputs are invalid campaign diagnostics and
must not enter analysis. Replacement jobs above use the active 3g.40gb MIG
slices that produced the completed focused-factorial runs.

The 384-token Qwen diagnostic `26474` completed 4,000/4,000 rows but failed the
predeclared quality gate: its four non-concise reasoning-requested cells had
16.25--24% truncation (the concise cell had 0%). Llama diagnostic `26477` was
stopped once the same budget problem was identified. Neither enters
confirmatory analysis. All active jobs above use a 768-token ceiling; their
quality metrics will be checked before any result is admitted.

## Historical focused-factorial status

- Complete initial-seed runs: Qwen `26384`, Mistral `26398`, Llama `26403`,
  Tulu-DPO `26421`, and Tulu-SFT `26406`.
- Phi `26422` exposed incompatibility in repository-provided remote model code
  with the installed Transformers cache API. The runner now defaults to native
  Transformers Phi-3 support. Smoke `26475` is complete; the 768-token initial
  full run is `26699`, and the focused seed-16101/16102 runs are `26714` and
  `26718`.
- Corrected Phi smoke `26475` completed in 90 seconds with exit status 0,
  200/200 expected rows, zero parse failures, and zero truncations.
- Replication `26424` failed because its data file was missing from the remote
  account. The file is now synchronized. Downstream jobs `26425`--`26435` were
  cancelled by the former `afterok` chain. The current focused replacements are:
  - Qwen: `26669`, `26673`;
  - Mistral: `26677`, `26681`;
  - Tulu-DPO: `26685`, `26686`;
  - Llama: `26706`, `26710`;
  - Tulu-SFT: `26722`, `26723`;
  - Phi: `26714`, `26718`.
