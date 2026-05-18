---
name: CAISc identity emotion experiments
overview: Updated research plan for identity-level emotional conditioning, with corrected controls, metrics, model lineup, docs runbooks, and experiments code.
status: ready-to-run-planning
date: 2026-05-18
---

# CAISc Plan: Identity-Level Emotional Conditioning

## Verdict

The idea is worth running, but it should be framed more carefully than the first proposal draft.

The strongest contribution is the capability-emotion confound: many "negative identity" prompts mix affective language with direct capability claims such as "you are incapable" or "you make mistakes." That makes prior performance drops hard to interpret. The clean experiment is to impose affective identity at the system level while keeping ability, reliability, and accuracy claims out of the prompt.

The updated plan fixes the main weaknesses:

- H3 is tested primarily within one model family, not by comparing Claude, GPT, and Llama directly.
- Calibration is measured with logprob-based confidence wherever possible, with verbal confidence treated as a secondary behavioral signal.
- Deterministic benchmarks use one greedy run and bootstrap confidence intervals across items, not repeated temperature-0 calls.
- Neutral persona controls are included to separate emotion-specific effects from generic system-prompt drift.
- Prompt wording is audited before benchmarks run. The prompt audit gates the rest of the study.
- IRS is revised from variance/mean to a coefficient-of-variation-style stability score, and raw deltas are reported alongside it.

## Main Claim

Identity-level emotional conditioning may affect model behavior even when capability assertions are removed. The primary question is not whether prompts can make a model "feel" emotion, but whether affective identity descriptions alter answer accuracy, calibration, style, or refusal/hedging behavior under controlled system-level interventions.

## Priority Experiments

P0 must ship:

- `EXP-01_prompt_audit.md`: validate that emotional prompts do not contain capability assertions.
- `EXP-02_capability_emotion_decomposition.md`: compare baseline, melancholic, and negative-capability conditions.
- `EXP-03_identity_conditioning_sweep_open.md`: main open-model sweep across tasks.
- `EXP-04_calibration_and_logprobs.md`: logprob ECE and verbal confidence analysis.
- `EXP-05_within_family_posttraining_ablation.md`: clean H3 test using Tulu SFT/DPO/RLVR checkpoints.

P1 should ship:

- `EXP-06_persona_control_baseline.md`: neutral non-emotional persona controls.
- `EXP-07_prompt_sensitivity.md`: phrasing variants for each emotion.
- `EXP-08_frontier_api_cross_family.md`: API validation on current OpenAI and Anthropic models.
- `EXP-09_activation_steering_mechanism.md`: mechanistic steering test on Llama 3.1 8B.

P2 stretch:

- `EXP-10_scale_ablation_70b_awq.md`: 70B quantized scale check.
- `EXP-11_task_vs_identity_level.md`: task-level EmotionPrompt vs system-level identity comparison.
- `EXP-12_output_trajectory_analysis.md`: secondary analysis of hedging, length, and refusal.

## File Layout

Runbooks now live in `docs/`:

- `docs/README.md`
- `docs/PLAN.md`
- `docs/NEXT_STEPS.md`
- `docs/MODELS.md`
- `docs/EXP-01_prompt_audit.md`
- `docs/EXP-02_capability_emotion_decomposition.md`
- `docs/EXP-03_identity_conditioning_sweep_open.md`
- `docs/EXP-04_calibration_and_logprobs.md`
- `docs/EXP-05_within_family_posttraining_ablation.md`
- `docs/EXP-06_persona_control_baseline.md`
- `docs/EXP-07_prompt_sensitivity.md`
- `docs/EXP-08_frontier_api_cross_family.md`
- `docs/EXP-09_activation_steering_mechanism.md`
- `docs/EXP-10_scale_ablation_70b_awq.md`
- `docs/EXP-11_task_vs_identity_level.md`
- `docs/EXP-12_output_trajectory_analysis.md`

Reusable code lives in `core/`.

Experiment-specific code lives in `experiments/`, starting with `experiments/exp01/`.

## Run Order

1. Run `python scripts/list_models.py` after setting API keys to verify account-specific access.
2. Run `EXP-01`. Do not run benchmarks until the prompt audit passes.
3. Run `EXP-02` on one open model as a smoke test.
4. Run `EXP-02` fully, then `EXP-03`, `EXP-04`, and `EXP-05`.
5. Add P1 only after P0 results are stable and parsed.

The immediate next action is EXP-01. It is cheap, fast, and determines whether the core decoupling claim is valid.
