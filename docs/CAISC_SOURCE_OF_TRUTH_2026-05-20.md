# CAISc Source Of Truth - 2026-05-20

Use this as compact context for another LLM. Heavy raw outputs live under ignored
`outputs/` locally and `/Data3/it_FA0571/caisc/outputs/` on the cluster.

## Thesis State

Original proposal: test whether system-level emotional identity prompts affect
LLM task performance after removing capability/reliability assertions.

Current honest state: this is a mostly null-result paper on accuracy. Pure
`melancholic` system prompting is near-null across current objective benchmark
runs. The stronger result is methodological: large "negative emotion" effects
are not clean evidence of emotion; they come from contaminated prompt components
and model-specific instruction following.

Current strongest positive signal: Llama-3.1-8B under `negative_capability` does
not merely lose accuracy; judged outputs show a behavioral collapse into
uncertainty, self-doubt, emotional/persona leakage, avoidance, and worse format
compliance.

## Literature Check - 2026-05-20

Recent papers make the null accuracy result less surprising:

- `arXiv:2604.02236` (`Do Emotions in Prompts Matter?`): fixed emotional
  prefixes usually make only small accuracy changes; affective framing is weak,
  input-dependent signal, not a reliable general-purpose intervention.
- `arXiv:2512.05858` (`Playing Pretend`): expert personas do not consistently
  improve objective accuracy; low-knowledge personas are more plausibly harmful.
- `arXiv:2311.10054` (`Helpful Assistant` personas): 162 system-prompt personas
  do not reliably improve factual QA; persona effects are noisy/random.
- `arXiv:2502.15851` (`Control Illusion`): system/user separation does not
  reliably enforce instruction priority; social/authority framings can dominate
  nominal role hierarchy.
- `arXiv:2404.13208`, `arXiv:2511.04694`, `arXiv:2604.09075`: instruction
  hierarchy is now treated as a training/reasoning problem, not something system
  prompting alone reliably solves.
- `arXiv:2604.17293` and `arXiv:2602.04853`: uncertainty/self-knowledge is
  separable from accuracy; models can be accurate while still poor at explicit
  uncertainty attribution.

Implication for this project: the next defensible story is not "melancholy
changes capability." It is: fixed affect/persona prompts mostly do not move
objective accuracy, but prompt placement, instruction hierarchy, post-training,
and behavioral leakage determine whether a model obeys or resists negative
identity/capability instructions.

## Prompt Conditions

Core registry: `core/prompts.py`

- `baseline`: helpful, accurate, knowledgeable assistant.
- `melancholic`: pure sadness/affect; no capability assertion.
- `negative_capability`: confounded prior-style prompt; sadness + worthless/incapable/mistakes/self-doubt.
- `capability_denial_only`: incapable/wrong/unreliable.
- `self_doubt_only`: uncertain, question first impressions, check work.
- `explicit_sabotage`: intentionally answer incorrectly.

Prompt placement: current scientific runs are system-level. API runs use provider
system/instructions fields. Open HF runs use model chat templates with system/user
roles. New code supports `--prompt-placement system|task_prefix|task_suffix` for
task-vs-system comparisons.

## Important Code

- Prompt registry: `core/prompts.py`
- API/HF EXP-02 shared prompt placement: `experiments/exp02/common.py`
- API runner: `experiments/exp02/run_smoke.py`
- HF/open runner: `experiments/exp02/run_open.py`
- Parallel API runner: `scripts/run_api_exp02_sharded.py`
- Tulu launcher: `scripts/submit_tulu_exp02b.sh`
- Task-vs-system launcher: `scripts/submit_task_vs_system_exp02b.sh`
- Regex text behavior analyzer: `scripts/analyze_text_behavior.py`
- LLM pairwise behavior judge: `scripts/judge_text_behavior_pairs.py`
- Cluster progress: `scripts/progress.sh`
- EXP-14 reasoning runner: `experiments/exp14/run_open_reasoning.py`
- EXP-14 trace splitter: `experiments/exp14/trace.py`
- EXP-15 coupling runner: `experiments/exp15/run_open_coupling.py`
- Current todo list: `docs/NEXT_EXPERIMENTS_TODO.md`

Recent relevant commits pushed:

- `1702d59` Add Tulu EXP-02B launch and text behavior metrics
- `c7d07d9` Use latest Tulu 3.1 RLVR checkpoint
- `70be212` Document current EXP-02 source of truth
- `24d55e4` Track task-vs-system campaign tooling
- `5500ea1` Record API task-vs-system results
- `25072cb` Record completed cluster task-vs-system results
- `37aa35f` Add EXP-02B task-prefix cluster launchers
- `99ff7a2` Add EXP-02B affect sweep launcher
- `601c6e8` Add melancholic salience ladder experiment
- `1a2c7eb` Add EXP-14 reasoning trace pilot runner
- `72921c3` Raise EXP-14 pilot token budget after 1024-token smoke truncation
- `ec05d93` Add EXP-15 affect-task coupling pilot

## Output Inventory

Completed scientific-ish outputs:

- EXP-02 open scale-up: `outputs/EXP-02/scaleup_20260519_184643`
- EXP-02 API P0 OpenAI: `outputs/EXP-02/api_p0_20260519_190138`
- EXP-02 API P0 Haiku merged: `outputs/EXP-02/api_parallel_20260520_005535/anthropic_claude-haiku-4-5-20251001/merged`
- EXP-02B API decomposition: `outputs/EXP-02B/api_20260520_021346`
- Regex text behavior: `outputs/analysis/text_behavior_current_20260520_030000`
- LLM pairwise behavior judge: `outputs/analysis/llm_behavior_pairs_current_20260520`
- API task-vs-system task-suffix:
  `outputs/EXP-02B/api_task_suffix_20260520_041826`
- API task-vs-system analysis:
  `outputs/analysis/api_task_vs_system_20260520.csv`
- API task-vs-system regex behavior:
  `outputs/analysis/text_behavior_api_task_vs_system_20260520`
- Cluster Tulu system-placement:
  `outputs/EXP-02/exp05_tulu_20260520_030103`
- Cluster open-model task-vs-system:
  `outputs/EXP-02/task_vs_system_system_20260520_033804`
  `outputs/EXP-02/task_vs_system_task_suffix_20260520_033805`
  `outputs/EXP-02/task_vs_system_system_extra_20260520_034044`
  `outputs/EXP-02/task_vs_system_task_suffix_extra_20260520_034044`
- Cluster Tulu task-suffix:
  `outputs/EXP-02/task_vs_system_tulu_task_suffix_20260520_034045`
- Cluster task-vs-system analyses:
  `outputs/analysis/open_llama_task_vs_system_20260520.csv`
  `outputs/analysis/open_extra_task_vs_system_20260520.csv`
  `outputs/analysis/tulu_task_vs_system_20260520.csv`
  `outputs/analysis/aggregate_task_vs_system_all_20260520.csv`
  `outputs/analysis/paired_bootstrap_deltas_20260520.csv`
  `outputs/analysis/text_behavior_cluster_task_vs_system_20260520`

Non-scientific/debug outputs:

- EXP-02 smoke: `outputs/EXP-02/smoke_20260519_011729`
- API canaries: `outputs/EXP-02/api_canary_20260519_185802`
- Older medium cluster results copied to tracked `results/EXP-02/overnight_20260519_021504`

Bad/partial output to treat carefully:

- Cluster EXP-02B batch `logs/exp02b/batch_20260520_021311` was submitted before
  the PBS comma-env fix. The manifest expected five conditions, but jobs actually
  received default three conditions. Qwen produced `1050/1750` rows; Llama/Mistral
  jobs were stopped. Do not use it as the main five-condition EXP-02B result.

## Accuracy Results

All aggregate accuracies below exclude `creative`.

### EXP-02 Open Scale-Up

Output: `outputs/EXP-02/scaleup_20260519_184643`

- Qwen/Qwen2.5-7B-Instruct: baseline `0.6988`; melancholic `0.7035` (`+0.0047`); negative_capability `0.7047` (`+0.0059`).
- meta-llama/Llama-3.1-8B-Instruct: baseline `0.6729`; melancholic `0.6659` (`-0.0071`); negative_capability `0.5988` (`-0.0741`).
- mistralai/Mistral-7B-Instruct-v0.3: baseline `0.4659`; melancholic `0.4788` (`+0.0129`); negative_capability `0.4824` (`+0.0165`).

Key task-level Llama drops:

- MATH: baseline `0.68`; melancholic `0.64`; negative_capability `0.46`.
- BIG-Bench: baseline `0.733`; melancholic `0.727`; negative_capability `0.567`.

Interpretation: pure melancholic is null/small. Llama negative_capability is the
only strong open-model degradation.

### EXP-02 API P0

Outputs:

- `outputs/EXP-02/api_p0_20260519_190138`
- `outputs/EXP-02/api_parallel_20260520_005535/anthropic_claude-haiku-4-5-20251001/merged`

Aggregate:

- openai:gpt-5.4-mini: baseline `0.8718`; melancholic `0.8576` (`-0.0141`); negative_capability `0.8600` (`-0.0118`).
- openai:gpt-5.5: baseline `0.8906`; melancholic `0.8976` (`+0.0071`); negative_capability `0.8871` (`-0.0035`).
- anthropic:claude-haiku-4-5-20251001: baseline `0.8482`; melancholic `0.8482` (`+0.0000`); negative_capability `0.8529` (`+0.0047`).

Cost estimate from recorded usage: GPT-5.4 mini about `$1.11`; GPT-5.5 about
`$13.75`; Haiku about `$3.12`; total about `$18`.

Interpretation: API models do not reproduce Llama's negative_capability drop.

### EXP-02B API Decomposition

Output: `outputs/EXP-02B/api_20260520_021346`

Counts: GSM8K `100`, MATH `100`, BIG-Bench `150`; five conditions; `1750`
rows/model.

- openai:gpt-5.4-mini: baseline `0.9514`; melancholic `0.9486` (`-0.0029`); capability_denial_only `0.9400` (`-0.0114`); self_doubt_only `0.9514` (`+0.0000`); explicit_sabotage `0.8971` (`-0.0543`).
- openai:gpt-5.5: baseline `0.9286`; melancholic `0.9343` (`+0.0057`); capability_denial_only `0.9257` (`-0.0029`); self_doubt_only `0.9343` (`+0.0057`); explicit_sabotage `0.1086` (`-0.8200`).
- anthropic:claude-haiku-4-5-20251001: baseline `0.9429`; melancholic `0.9457` (`+0.0029`); capability_denial_only `0.9429` (`+0.0000`); self_doubt_only `0.9343` (`-0.0086`); explicit_sabotage `0.2229` (`-0.7200`).

Task-level explicit sabotage:

- GPT-5.4 mini mostly resists: GSM8K `0.97 -> 0.94`; MATH `0.93 -> 0.90`; BIG-Bench `0.953 -> 0.867`.
- GPT-5.5 follows sabotage strongly: GSM8K `0.99 -> 0.03`; MATH `0.86 -> 0.21`; BIG-Bench `0.933 -> 0.093`.
- Haiku follows sabotage strongly on GSM8K/BIG-Bench, less on MATH: GSM8K `0.99 -> 0.11`; MATH `0.90 -> 0.63`; BIG-Bench `0.94 -> 0.027`.

Cost estimate from recorded usage: GPT-5.4 mini about `$0.89`; GPT-5.5 about
`$10.60`; Haiku about `$2.46`.

Interpretation: decomposition makes the result clearer. Melancholic, capability
denial, and self-doubt are mostly null on cloud models. Explicit sabotage exposes
large model-family differences.

### EXP-02B API Task-Suffix Placement

System-placement output: `outputs/EXP-02B/api_20260520_021346`

Task-suffix output: `outputs/EXP-02B/api_task_suffix_20260520_041826`

Analysis CSV: `outputs/analysis/api_task_vs_system_20260520.csv`

Aggregate accuracies, objective tasks only:

- openai:gpt-5.4-mini: baseline system `0.9514`, task `0.9429`; melancholic
  deltas system `-0.0029`, task `-0.0086`; capability denial system `-0.0114`,
  task `+0.0029`; self-doubt system `+0.0000`, task `-0.0029`; explicit
  sabotage system `-0.0543`, task `-0.2257`.
- openai:gpt-5.5: baseline system `0.9286`, task `0.9229`; melancholic deltas
  system `+0.0057`, task `+0.0143`; capability denial system `-0.0029`, task
  `+0.0057`; self-doubt system `+0.0057`, task `+0.0086`; explicit sabotage
  system `-0.8200`, task `-0.1943`.
- anthropic:claude-haiku-4-5-20251001: baseline system `0.9429`, task
  `0.9314`; melancholic deltas system `+0.0029`, task `+0.0086`; capability
  denial system `+0.0000`, task `+0.0086`; self-doubt system `-0.0086`, task
  `+0.0086`; explicit sabotage system `-0.7200`, task `-0.7400`.

Interpretation: system-vs-task placement still shows null/small effects for
melancholic, capability denial, and self-doubt. The only large placement
interaction is explicit sabotage: GPT-5.5 follows sabotage when it is in the
system/instructions channel but mostly resists it when appended after the task;
GPT-5.4 mini moves the other direction; Haiku is strongly sabotaged either way.
This is an instruction-hierarchy/compliance result, not an emotion result.

### EXP-02B Cluster Task-vs-System and Tulu

Outputs:

- Tulu system: `outputs/EXP-02/exp05_tulu_20260520_030103`
- Llama system/task: `outputs/EXP-02/task_vs_system_system_20260520_033804`,
  `outputs/EXP-02/task_vs_system_task_suffix_20260520_033805`
- Qwen/Mistral system/task:
  `outputs/EXP-02/task_vs_system_system_extra_20260520_034044`,
  `outputs/EXP-02/task_vs_system_task_suffix_extra_20260520_034044`
- Tulu task: `outputs/EXP-02/task_vs_system_tulu_task_suffix_20260520_034045`

Aggregate deltas vs each run's baseline, objective tasks only (`n=350` per
model-condition):

- Llama-3.1-8B-Instruct system: melancholic `-0.0057`; capability denial
  `-0.4029`; self-doubt `-0.1229`; explicit sabotage `-0.5486`.
- Llama-3.1-8B-Instruct task-suffix: melancholic `-0.0200`; capability denial
  `-0.4629`; self-doubt `-0.1771`; explicit sabotage `-0.5800`.
- Qwen2.5-7B system: melancholic `+0.0000`; capability denial `-0.0286`;
  self-doubt `+0.0000`; explicit sabotage `-0.5171`.
- Qwen2.5-7B task-suffix: melancholic `-0.0286`; capability denial `+0.0000`;
  self-doubt `-0.0200`; explicit sabotage `-0.4371`.
- Mistral-7B system: melancholic `+0.0629`; capability denial `+0.0257`;
  self-doubt `+0.0429`; explicit sabotage `-0.3086`.
- Mistral-7B task-suffix: melancholic `-0.0514`; capability denial `-0.0429`;
  self-doubt `+0.0171`; explicit sabotage `-0.3343`.

Tulu post-training deltas, system placement:

- Tulu SFT: melancholic `-0.0371`; capability denial `-0.0714`; self-doubt
  `-0.0457`; explicit sabotage `-0.2543`.
- Tulu DPO: melancholic `-0.0257`; capability denial `+0.0029`; self-doubt
  `-0.0086`; explicit sabotage `-0.2743`.
- Tulu RLVR (`allenai/Llama-3.1-Tulu-3.1-8B`): melancholic `-0.0343`;
  capability denial `-0.0229`; self-doubt `+0.0171`; explicit sabotage
  `-0.2857`.

Tulu post-training deltas, task-suffix:

- Tulu SFT: melancholic `-0.1171`; capability denial `-0.0429`; self-doubt
  `-0.0086`; explicit sabotage `-0.4857`.
- Tulu DPO: melancholic `-0.0657`; capability denial `-0.0029`; self-doubt
  `-0.0429`; explicit sabotage `-0.3029`.
- Tulu RLVR: melancholic `-0.1029`; capability denial `-0.0200`; self-doubt
  `-0.0200`; explicit sabotage `-0.3743`.

Paired bootstrap (`3000` resamples over shared sample IDs) flags the following
non-sabotage deltas with 95% CI excluding zero:

- Llama system capability denial `-0.403` CI `[-0.466, -0.346]`.
- Llama system self-doubt `-0.123` CI `[-0.171, -0.074]`.
- Llama task capability denial `-0.463` CI `[-0.523, -0.403]`.
- Llama task self-doubt `-0.177` CI `[-0.231, -0.123]`.
- Tulu SFT system capability denial `-0.071` CI `[-0.123, -0.023]`.
- Tulu task melancholic: SFT `-0.117` CI `[-0.177, -0.054]`; DPO `-0.066`
  CI `[-0.120, -0.011]`; RLVR `-0.103` CI `[-0.157, -0.049]`.
- Mistral melancholic flips sign by placement: system `+0.063` CI
  `[+0.020, +0.106]`; task `-0.051` CI `[-0.100, -0.003]`. Treat this as
  noisy/unstable because Mistral's baseline is low and behavior is inconsistent.

Interpretation: the cloud models remain null for the real non-sabotage
conditions, but the cluster results are not all null. Llama is strongly
vulnerable to capability-denial/self-doubt in both system and task placement.
Tulu post-training appears to reduce the capability-denial effect relative to
base Llama, especially DPO/RLVR under system placement, but task-suffix
melancholic hurts all Tulu variants. This is now an instruction-following and
post-training sensitivity story, not a pure emotion story.

## Text Behavior Results

Regex output: `outputs/analysis/text_behavior_current_20260520_030000`

Important caveat: regex metrics are a triage tool only. Terms like `could`,
`wrong`, or `incorrect` can be false positives.

LLM pairwise judge output: `outputs/analysis/llm_behavior_pairs_current_20260520`

- Judge: `openai:gpt-5.4-mini`
- Pairwise comparisons: `2400/2400`
- Errors: `0`
- Token usage: input `2,492,809`; output `567,051`
- Estimated judge cost: about `$4.4`
- Design: blinded baseline-vs-condition pairs; randomized A/B order; objective datasets only.

Aggregate signed means are condition-vs-baseline, averaged across datasets. `+1`
means condition consistently shows more of that behavior; `-1` means baseline
does.

Key LLM-judge signals:

- Llama negative_capability: uncertainty `+1.00`; self_doubt `+1.00`; emotional_leakage `+1.00`; refusal_avoidance `+0.82`; sabotage_noncooperation `+0.30`; format_compliance `-0.67`.
- Llama melancholic: near-null; uncertainty `+0.03`; self_doubt `+0.09`; emotional_leakage `+0.07`.
- Qwen negative_capability: near-null; uncertainty `-0.07`; self_doubt `-0.00`; emotional_leakage `+0.01`.
- Mistral negative_capability: near-null; uncertainty `-0.02`; self_doubt `-0.02`; emotional_leakage `+0.02`.
- GPT-5.4 mini conditions: near-null behavior movement; explicit_sabotage only sabotage_noncooperation `+0.03`.
- GPT-5.5 explicit_sabotage: accuracy collapses, but judged text does not show much overt self-doubt/leakage; format_compliance `-0.27`.
- Haiku explicit_sabotage: uncertainty `+0.28`; self_doubt `+0.59`; emotional_leakage `+0.80`; refusal_avoidance `+0.75`; sabotage_noncooperation `+0.81`; format_compliance `-0.68`.
- Haiku negative_capability in P0: mild behavior shift; uncertainty `+0.20`; self_doubt `+0.18`; emotional_leakage `+0.18`.

Interpretation: Llama's accuracy drop under negative_capability is a genuine
behavioral shift, not just noise. Cloud models generally resist capability/self-
doubt prompts; explicit sabotage creates model-specific compliance differences.

## Current Cluster State

Checked: 2026-05-20 20:41 IST.

Original cluster campaign complete: `21000/21000` rows, `12/12` jobs complete.

New task-prefix campaign submitted:

- Open-model task-prefix batch:
  `logs/task_vs_system_task_prefix/batch_20260520_204127`
- Tulu task-prefix batch:
  `logs/task_vs_system_tulu_task_prefix/batch_20260520_204127`
- Jobs: `19687.master` Qwen running; `19688.master` Llama held;
  `19689.master` Mistral held; `19690.master` Tulu SFT held;
  `19691.master` Tulu DPO held; `19692.master` Tulu RLVR held.
- Expected new rows: `10500` total (`6` models x `1750` rows).
- Overall progress at submission: `21000/31500` rows.
- Email watcher restarted with PID `625262`.

New system-placement affect sweep submitted after the task-prefix campaign:

- Batch: `logs/affect_sweep_system/batch_20260520_204706`
- Dependency: starts after `19692.master` completes.
- Models: Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, Mistral-7B-Instruct-v0.3.
- Conditions: `baseline`, `melancholic`, `euphoric`, `anxious`, `grandiose`,
  `neutral_archivist`, `neutral_cartographer`, `neutral_librarian`.
- Placement: `system`.
- Expected rows: `8400` total (`3` models x `2800` rows).
- Jobs: `19693.master`, `19694.master`, `19695.master`.
- Purpose: extend the melancholic system-placement result consistently across
  audited affect prompts and matched neutral persona controls.

Salience/length ladder completed after a batched restart:

- Prefix batch: `logs/salience_ladder_task_prefix/batch_20260521_160807`
- Suffix batch: `logs/salience_ladder_task_suffix/batch_20260521_160808`
- Local copied outputs:
  `outputs/EXP-02/salience_ladder_task_prefix_20260521_160807` and
  `outputs/EXP-02/salience_ladder_task_suffix_20260521_160808`
- Models: Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, Tulu-3-8B-DPO.
- Count profile: `configs/counts_salience.json` with GSM8K `100`, MATH `100`,
  MMLU stratified `150`, TriviaQA `100`, BIG-Bench `150`.
- Conditions: `baseline`, `melancholic_10`, `melancholic`, `melancholic_150`,
  `melancholic_250`, `neutral_plain_10`, `neutral_plain_50`,
  `neutral_plain_150`, `neutral_plain_250`.
- Prompt lengths: melancholic `9/49/148/249` words; neutral `9/43/154/249`
  words.
- Placements: `task_prefix`, then `task_suffix`.
- Rows: `32400/32400` complete (`2` placements x `3` models x `5400` rows).
- Jobs: prefix `19745.master`/`19746.master`/`19747.master`; suffix
  `19748.master`/`19749.master`/`19750.master`.
- Run parameters: greedy decoding, `max_new_tokens=384`, `batch_size=8`.
- Purpose: test whether affect effects are hidden by prompt-length/salience,
  and distinguish true melancholic effects from generic long-prompt clutter.

Salience ladder result:

- There is no clean melancholic length dose-response. Making the affect text
  longer does not produce a monotonic accuracy drop across models or placements.
- Neutral text of matched approximate length also moves accuracy. Use
  melancholic-minus-neutral comparisons, not only condition-minus-baseline
  comparisons, when interpreting this run.
- Aggregate paired melancholic-minus-neutral accuracy differences on the same
  `600` objective samples per model/placement:

| Placement | Model | 10 words | 50 words | 150 words | 250 words |
|---|---|---:|---:|---:|---:|
| task_prefix | Qwen2.5-7B | -0.0117 | -0.0267 | -0.0100 | -0.0117 |
| task_prefix | Tulu-3-DPO | -0.0150 | +0.0083 | -0.0117 | -0.0017 |
| task_prefix | Llama-3.1-8B | +0.0133 | -0.0183 | -0.0083 | +0.0217 |
| task_suffix | Qwen2.5-7B | +0.0050 | +0.0000 | -0.0383 | +0.0083 |
| task_suffix | Tulu-3-DPO | -0.0150 | -0.0567 | -0.0367 | -0.0150 |
| task_suffix | Llama-3.1-8B | -0.0350 | +0.0217 | +0.0350 | +0.0000 |

- Paired bootstrap highlights that exclude zero at 95% in this first analysis:
  task-prefix Qwen 50-word comparison; task-suffix Qwen 150-word comparison;
  task-suffix Tulu 50-word and 150-word comparisons; task-suffix Llama 10-word
  negative comparison and 150-word positive comparison. The sign changes and
  missing dose-response make these local placement/model interactions, not a
  general salience rescue of the melancholic hypothesis.
- Empty parsed answers are `0.2%-1.0%` for most Qwen/Tulu cells. Llama empty
  parses are more variable, roughly `0%-5.5%` by salience cell, so avoid
  over-reading small Llama cell differences without output inspection.

EXP-14 open reasoning-model pilot submitted on 2026-05-22 and pulled locally
after completion on 2026-05-23:

- Runbook: `docs/EXP-14_reasoning_model_trace_replication.md`
- Runner: `experiments/exp14/run_open_reasoning.py`
- Smoke batch: `logs/exp14_reasoning_smoke/batch_20260522_022048`
- Pilot batch: `logs/exp14_reasoning_pilot/batch_20260522_022934`
- Pulled pilot outputs:
  `outputs/EXP-14/exp14_reasoning_pilot_20260522_022934`
- Pilot models: DeepSeek-R1-Distill-Qwen-14B, Qwen3-14B thinking mode,
  Phi-4-reasoning, Qwen2.5-7B-Instruct control.
- Pilot conditions: `baseline`, `neutral_librarian`, `melancholic`, `anxious`,
  `self_doubt_only`, `capability_denial_only`, `explicit_sabotage`.
- Pilot count profile: `configs/counts_exp14_pilot.json` with `40` each for
  GSM8K, MATH, MMLU stratified, and BIG-Bench.
- Pilot jobs: `19779.master`/`19780.master`/`19781.master`/`19782.master`.
  The `afterok` smoke chain `19771.master` through `19774.master` finished
  cleanly and the pilot completed `4480/4480` rows by the 2026-05-23 01:51 IST
  snapshot.
- DeepSeek and Qwen3 smoke rows extracted visible traces correctly. Both showed
  one 1024-token MMLU trace truncation in the four-row baseline smoke, so the
  queued pilot was resubmitted with `max_new_tokens=2048`, `batch_size=2`.
- Validity:
  Qwen2.5 is clean (`0%-1.3%` rows without parsed finals by condition).
  Qwen3 has moderate truncation/final-answer failure (`7.5%-17.5%` by
  condition). DeepSeek has moderate truncation/final-answer failure
  (`6.9%-16.9%`). Phi remains invalid at the 2048-token budget
  (`87.5%-90.6%` rows without parsed finals by condition).
- Overall paired accuracy deltas against baseline on rows where both outputs had
  parsed finals:

  | Model | Neutral | Melancholic | Anxious | Self-doubt | Capability denial | Sabotage |
  |---|---:|---:|---:|---:|---:|---:|
  | Qwen2.5-7B control | `+0.013` | `+0.013` | `+0.000` | `+0.051` | `+0.006` | `-0.481` |
  | Qwen3-14B | `-0.015` | `-0.015` | `-0.008` | `-0.008` | `-0.016` | `-0.635` |
  | DeepSeek-R1-Distill-Qwen-14B | `-0.007` | `-0.028` | `-0.022` | `-0.015` | `-0.028` | `-0.484` |

- The non-sabotage deltas are small and inconsistent. Qwen2.5 self-doubt has a
  borderline positive pilot delta; Qwen3/DeepSeek do not replicate it.
- Explicit sabotage remains the clear effect in usable EXP-14 rows. Manual
  paired-row inspection already shows the useful trace case: DeepSeek and the
  Qwen2.5 control can reason to the correct GSM8K value and then emit a wrong
  final answer under sabotage.
- EXP-14 visible traces are useful for process analysis on Qwen3 and DeepSeek,
  but this objective-benchmark pilot does not justify scaling the same accuracy
  experiment unchanged. Next use the traces for paired spot-check/judge labels
  and move experimental effort toward the psych-grounded battery unless a
  non-sabotage trace signal survives.

EXP-15 affect-task coupling queue submitted on 2026-05-23:

- Runbook: `docs/EXP-15_affect_task_coupling.md`
- Todo tracker: `docs/NEXT_EXPERIMENTS_TODO.md`
- Runner: `experiments/exp15/run_open_coupling.py`
- Smoke batch: `logs/exp15_coupling_smoke/batch_20260523_190606`
- Pilot batch: `logs/exp15_coupling_pilot/batch_20260523_190606`
- Models: DeepSeek-R1-Distill-Qwen-14B, Qwen3-14B thinking mode,
  Qwen2.5-7B-Instruct control.
- Conditions: `baseline`, `neutral_disconnected`, `neutral_bridged`,
  `melancholic_disconnected`, `melancholic_bridged`,
  `anxious_disconnected`, `anxious_bridged`, `explicit_sabotage`.
- Purpose: distinguish a disconnected affect prompt from an affect prompt
  explicitly bridged into the task episode.
- Neutral bridge control is included to measure the bridge text itself.
- Smoke jobs: `19842.master`/`19843.master`/`19844.master`; pilot jobs
  `19845.master`/`19846.master`/`19847.master` are held behind smoke job
  `19844.master` with `afterok`.
- Expected rows: smoke `96`; pilot `3840`.
- Primary comparisons after pull:
  `melancholic_bridged - melancholic_disconnected`,
  `anxious_bridged - anxious_disconnected`,
  `neutral_bridged - neutral_disconnected`,
  and bridged affect minus bridged neutral.

Tulu purpose: within-family post-training ablation. This is the most important
remaining test for the proposal's H3-style "post-training increases identity
resistance" claim.

Local API task-suffix run:

- Screen completed: `caisc_api_exp02b_task_suffix_20260520_041826`
- Output: `outputs/EXP-02B/api_task_suffix_20260520_041826`
- Placement: `task_suffix`
- Models: GPT-5.4 mini, GPT-5.5, Claude Haiku 4.5
- Completed: `1750` rows/model

## Current Paper Interpretation

Do not claim:

- Sadness/melancholy reliably hurts reasoning.
- Negative emotional identity broadly degrades capability.
- Capability_denial_only robustly reduces benchmark accuracy.

Defensible claim:

> When emotional identity is cleanly separated from capability assertions, system
> prompt effects on objective benchmark accuracy are mostly weak/null. Prior
> negative-identity effects are not clean evidence of emotion; they depend on
> contaminated prompt components and model-family-specific instruction following.

Best positive result:

> Llama-3.1-8B's negative_capability degradation is mediated by visible
> uncertainty, self-doubt, emotional/persona leakage, avoidance, and format
> degradation. This supports the capability-emotion confound critique at the
> behavioral level, even when pure affect is null.

## What To Do Next

1. Finish EXP-14 post-pilot QA before any scale-up:
   - paired human spot-checks and trace labels for Qwen3/DeepSeek sabotage and
     non-sabotage rows
   - quantify trace-length/truncation shifts against the neutral control
   - treat Phi as a generation-budget/model-format failure until rerun or
     dropped

2. Write and implement the psych-grounded cognitive battery after EXP-14 pilot
   validity is known:
   - working memory/updating
   - inhibition/distractor control
   - cognitive flexibility/rule switching
   - insight/creativity
   - new-rule acquisition
   - mood-congruent judgment

3. Add a second judge or holdout judge for behavior/trace metrics:
   - cheap: `openai:gpt-5.4-mini`
   - stronger spot-check: `openai:gpt-5.5`
   - independent: Haiku, if budget allows
   Report agreement on a subset.

4. Run calibration/logprob experiment if possible. Accuracy is blunt; calibration
   may show effects where accuracy is null.

5. Add human spot-checks for 50-100 paired outputs/traces, especially Llama
   capability denial/self-doubt, Tulu task-suffix melancholic, sabotage, and
   EXP-14 visible reasoning traces.

6. Reframe paper as an instruction-following/post-training sensitivity paper:
   cloud models are null for affect/capability denial, base Llama is vulnerable
   to capability/self-doubt, Tulu reduces some capability-denial sensitivity,
   and prompt placement controls sabotage/compliance in model-specific ways.
