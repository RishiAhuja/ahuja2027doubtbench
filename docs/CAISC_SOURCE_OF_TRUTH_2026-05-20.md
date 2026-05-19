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

Recent relevant commits pushed:

- `1702d59` Add Tulu EXP-02B launch and text behavior metrics
- `c7d07d9` Use latest Tulu 3.1 RLVR checkpoint

## Output Inventory

Completed scientific-ish outputs:

- EXP-02 open scale-up: `outputs/EXP-02/scaleup_20260519_184643`
- EXP-02 API P0 OpenAI: `outputs/EXP-02/api_p0_20260519_190138`
- EXP-02 API P0 Haiku merged: `outputs/EXP-02/api_parallel_20260520_005535/anthropic_claude-haiku-4-5-20251001/merged`
- EXP-02B API decomposition: `outputs/EXP-02B/api_20260520_021346`
- Regex text behavior: `outputs/analysis/text_behavior_current_20260520_030000`
- LLM pairwise behavior judge: `outputs/analysis/llm_behavior_pairs_current_20260520`

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

Checked: 2026-05-20 03:25 IST.

Active batch: `logs/exp05_tulu/batch_20260520_030103`

- `19622.master` `allenai/Llama-3.1-Tulu-3-8B-SFT`: `739/1750`, running.
- `19623.master` `allenai/Llama-3.1-Tulu-3-8B-DPO`: `0/1750`, held after SFT.
- `19624.master` `allenai/Llama-3.1-Tulu-3.1-8B`: `0/1750`, held after DPO.
- Batch total: `739/5250` rows.
- Email watcher: PID `3447886`.

Tulu purpose: within-family post-training ablation. This is the most important
remaining test for the proposal's H3-style "post-training increases identity
resistance" claim.

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

1. Let Tulu finish, pull results, and analyze the SFT -> DPO -> RLVR trend.
   This decides whether the post-training identity-resistance story survives.

2. Rerun corrected open-model EXP-02B for Qwen/Llama/Mistral if cluster time
   allows. The earlier EXP-02B open batch was bad because PBS dropped five
   conditions.

3. Run task-vs-system comparison:
   - same conditions as system prompt
   - same conditions appended to task prompt
   This directly connects to EmotionPrompt/NegativePrompt literature.

4. Add a second judge or holdout judge for behavior metrics:
   - cheap: `openai:gpt-5.4-mini`
   - stronger spot-check: `openai:gpt-5.5`
   - independent: Haiku, if budget allows
   Report agreement on a subset.

5. Run calibration/logprob experiment if possible. Accuracy is blunt; calibration
   may show effects where accuracy is null.

6. Add human spot-checks for 50-100 pairwise outputs, especially Llama
   negative_capability and Haiku explicit_sabotage.

7. Reframe paper as a methodological null-result paper, not an emotional
   degradation paper.
