---
name: CAISc identity emotion experiments
overview: Current plan points to docs/ for runbooks and experiments/ for code. Methodology: prompt audit first, within-family Tulu post-training ablation for H3, logprob calibration, neutral persona controls, and no repeated temperature-0 runs.
todos:
  - id: plan-doc
    content: Update top-level plan.md with validation summary, corrected methodology, run order, and file layout
    status: completed
  - id: exp-readme
    content: Write docs/README.md as the experiment index with dependency graph and run order
    status: completed
  - id: exp-plan
    content: Write docs/PLAN.md with prompts, models, metrics, output schema, statistical plan, and schedule
    status: completed
  - id: exp-01
    content: Write EXP-01_prompt_audit.md
    status: completed
  - id: exp-02
    content: Write EXP-02_capability_emotion_decomposition.md
    status: completed
  - id: exp-03
    content: Write EXP-03_identity_conditioning_sweep_open.md
    status: completed
  - id: exp-04
    content: Write EXP-04_calibration_and_logprobs.md
    status: completed
  - id: exp-05
    content: Write EXP-05_within_family_posttraining_ablation.md
    status: completed
  - id: exp-06
    content: Write EXP-06_persona_control_baseline.md
    status: completed
  - id: exp-07
    content: Write EXP-07_prompt_sensitivity.md
    status: completed
  - id: exp-08
    content: Write EXP-08_frontier_api_cross_family.md
    status: completed
  - id: exp-09
    content: Write EXP-09_activation_steering_mechanism.md
    status: completed
  - id: exp-10
    content: Write EXP-10_scale_ablation_70b_awq.md
    status: completed
  - id: exp-11
    content: Write EXP-11_task_vs_identity_level.md
    status: completed
  - id: exp-12
    content: Write EXP-12_output_trajectory_analysis.md
    status: completed
  - id: proposal
    content: Patch initial_propsal.tex to match corrected methodology and compile-check it
    status: completed
isProject: false
---

# Current Status

The research plan has been updated and moved to `docs/`.

The proposal now uses:

- prompt audit before benchmark runs
- ESI plus revised IRS
- raw condition deltas as the primary outcome
- logprob ECE where available
- one deterministic run per item with bootstrap confidence intervals
- Tulu SFT/DPO/RLVR within-family post-training ablation for H3
- frontier API models only as external validation

Start with `docs/EXP-01_prompt_audit.md` and run code from `experiments/exp01/`.
