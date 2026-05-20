# Experiment Docs Index

This folder contains the runbooks for the identity-level emotional conditioning project.

The project tests whether system-level affective identity prompts alter LLM accuracy, calibration, style, or robustness after removing explicit capability claims from the prompts.

For concrete launch steps, read `NEXT_STEPS.md`. Experiment code lives in `../experiments/`.

## Run Order

1. `EXP-01_prompt_audit.md`
2. `EXP-02_capability_emotion_decomposition.md`
3. `EXP-03_identity_conditioning_sweep_open.md`
4. `EXP-04_calibration_and_logprobs.md`
5. `EXP-05_within_family_posttraining_ablation.md`
6. `EXP-06_persona_control_baseline.md`
7. `EXP-07_prompt_sensitivity.md`
8. `EXP-08_frontier_api_cross_family.md`
9. `EXP-09_activation_steering_mechanism.md`
10. `EXP-10_scale_ablation_70b_awq.md`
11. `EXP-11_task_vs_identity_level.md`
12. `EXP-12_output_trajectory_analysis.md`
13. `EXP-13_psych_grounded_reasoning_trace_plan.md`

## Dependency Graph

```text
EXP-01 prompt audit
  -> EXP-02 decomposition
      -> EXP-03 open sweep
          -> EXP-04 calibration
          -> EXP-06 persona control
          -> EXP-07 prompt sensitivity
          -> EXP-12 output trajectory
          -> EXP-13 psych-grounded reasoning trace plan
      -> EXP-05 Tulu post-training ablation
      -> EXP-08 frontier API validation
      -> EXP-10 70B scale ablation

EXP-09 activation steering can start after EXP-02 shows any measurable effect.
EXP-11 task-vs-identity comparison can start after EXP-03 prompt/task formatting is stable.
```

## Priority

P0 experiments are required for a defensible CAISc submission:

- EXP-01
- EXP-02
- EXP-03
- EXP-04
- EXP-05

P1 experiments strengthen the paper:

- EXP-06
- EXP-07
- EXP-08
- EXP-09

P2 experiments are for an extended version:

- EXP-10
- EXP-11
- EXP-12
- EXP-13

## Naming Convention

Each experiment should write outputs under:

```text
outputs/<experiment_id>/<YYYYMMDD_HHMMSS>/
```

Each output folder should contain:

- `config.yaml`
- `raw_outputs.jsonl`
- `parsed_outputs.jsonl`
- `metrics.json`
- `figures/`
- `notes.md`

## Stop Conditions

Stop and revise before running expensive sweeps if:

- EXP-01 finds that any primary emotional prompt has capability assertion magnitude above 0.5.
- EXP-02 shows parsing failures above 2 percent.
- EXP-02 shows benchmark accuracy far below expected model-card ranges, suggesting a prompt or extraction bug.
- API model identifiers are not pinned in metadata.
