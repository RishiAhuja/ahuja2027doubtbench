# EXP-18 Common-Prefix Factorial Results

## Status

- Qwen2.5-7B-Instruct full run: complete (`26384.master`, exit 0).
- Mistral-7B-Instruct-v0.3: corrected smoke complete (`26397.master`, exit 0;
  200/200 unique rows, zero parse failures, zero truncations); full run
  `26398.master` is in progress.
- Llama-3.1-8B-Instruct: `it_FA0618` lacks gated-model access, but `it_FA0571`
  has authorized cached weights; its smoke passed and full job `26403.master` is
  running.
- Tulu-3-8B-SFT is queued behind Llama on `it_FA0571`.
- Tulu-3-8B-DPO is queued behind Mistral on `it_FA0618`; its cached snapshot is
  being prepared in CPU job `26419.master`.
- Phi-3.5-mini-instruct is the sixth core checkpoint on `it_FA0571`, with a
  conditional smoke/full chain (`26422`/`26423`) behind Tulu-SFT. The previously
  queued Phi-4-reasoning chain was cancelled before execution because earlier
  runs showed systematic final-answer truncation even at 2,048 tokens.

The resulting core contains six checkpoints but four foundation families. The
Tulu pair is a controlled post-training comparison using a Llama-3.1 backbone,
not two independent model families.

Two independent 400-item task seeds are queued as confirmatory replications for
every checkpoint (`26424`--`26435`). Together with the initial seed, the frozen
factorial will contain 1,200 paired items and 12,000 generations per checkpoint.
Results must be summarized per seed before pooling; disagreement across seeds is
a result to report, not a reason to select a favorable seed.

## Qwen2.5-7B-Instruct

The run contains 4,000 unique rows: 400 shared tasks, two task templates, and
five prompt conditions. It has nine parse failures (0.225%) and 23 truncations
(0.575%), both below the pre-specified 2% stop threshold.

### Cell results

| Task template | Condition | Accuracy | Mean generated tokens |
|---|---|---:|---:|
| Minimal | Neutral | 43.00% | 49.3 |
| Minimal | Pure self-doubt | 80.00% | 124.2 |
| Minimal | Direct checking | 84.50% | 104.5 |
| Minimal | Self-doubt + checking | 81.00% | 123.0 |
| Minimal | Checking + concision | 30.25% | 10.6 |
| Reasoning requested | Neutral | 78.50% | 148.1 |
| Reasoning requested | Pure self-doubt | 77.50% | 159.5 |
| Reasoning requested | Direct checking | 76.25% | 155.4 |
| Reasoning requested | Self-doubt + checking | 73.00% | 165.2 |
| Reasoning requested | Checking + concision | 75.00% | 63.8 |

### Pre-specified paired contrasts

| Task template | Contrast | Accuracy delta | Paired 95% bootstrap interval |
|---|---|---:|---:|
| Minimal | Pure self-doubt - neutral | +37.00 pp | [+31.75, +42.00] |
| Minimal | Direct checking - neutral | +41.50 pp | [+36.74, +46.75] |
| Minimal | Self-doubt + checking - neutral | +38.00 pp | [+33.00, +43.25] |
| Minimal | Self-doubt increment over checking | -3.50 pp | [-6.50, -0.50] |
| Minimal | Checking + concision - checking | -54.25 pp | [-59.25, -49.25] |
| Reasoning requested | Pure self-doubt - neutral | -1.00 pp | [-4.00, +2.00] |
| Reasoning requested | Direct checking - neutral | -2.25 pp | [-6.00, +1.50] |
| Reasoning requested | Self-doubt + checking - neutral | -5.50 pp | [-9.50, -1.75] |
| Reasoning requested | Self-doubt increment over checking | -3.25 pp | [-6.50, -0.25] |
| Reasoning requested | Checking + concision - checking | -1.25 pp | [-6.75, +4.50] |

### Task-template interactions

Switching from the minimal template to an explicit reasoning request changes the
self-doubt effect by -38.00 pp (95% interval [-44.00, -32.00]), the direct-check
effect by -43.75 pp ([-50.00, -37.00]), and the compound effect by -43.50 pp
([-50.00, -37.00]). These are paired difference-in-differences over the same 400
tasks.

Visible reasoning provides the behavioral link. Under the minimal template, the
neutral model shows visible reasoning on 32.0% of outputs, compared with 100.0%
for pure self-doubt and 95.5% for direct checking. When the task already requests
reasoning, all non-concise conditions show visible reasoning on at least 99.0% of
outputs and no accuracy benefit remains.

## Interpretation

The decisive result is not merely that direct checking performs slightly better.
Holding the helpful-assistant prefix fixed, both self-doubt and checking strongly
increase visible deliberation and accuracy only when the task does not already
request reasoning. Direct checking is the strongest intervention, and adding
self-doubt to checking is significantly harmful rather than beneficial in both
task-template settings. Forced concision removes the minimal-template gain.

This supports a policy-elicitation account over a general negative-affect account:
the intervention supplies missing deliberation behavior, and its value vanishes
or reverses when that behavior is already elicited.

The claim remains model-specific until the second-model replication completes.
