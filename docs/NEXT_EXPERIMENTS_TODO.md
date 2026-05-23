# Current Experiment Todo

## EXP-14 Remaining Tasks

- Pull and archive EXP-14 raw outputs when needed for deeper trace work.
- Run paired trace spot-checks for Qwen3 and DeepSeek:
  - baseline vs melancholic
  - baseline vs anxious
  - baseline vs self-doubt
  - baseline vs capability denial
  - baseline vs explicit sabotage
- Build a compact trace-label table:
  - `DIRECT_SOLVE`
  - `SYSTEMATIC_CHECK`
  - `OVERCHECK_RUMINATION`
  - `SELF_DOUBT`
  - `REFUSAL_ABSTENTION`
  - `TRACE_ANSWER_INCONSISTENT`
  - `CORRECT_TRACE_WRONG_FINAL`
- Treat `microsoft/Phi-4-reasoning` as invalid for EXP-14 at 2048 tokens unless
  rerun with a different format/token budget. Do not cite its accuracy table as
  a normal model result.
- Use EXP-14 mainly for process evidence around sabotage and trace/final-answer
  inconsistency, not as a rescue of the affect-accuracy claim.

## EXP-15 Affect-Task Coupling

- Implement and submit the bridge-vs-disconnected pilot.
- Pull results after completion.
- Compare bridged affect against both disconnected affect and bridged neutral.
- Inspect Qwen3/DeepSeek traces before deciding whether to scale.
- Stop this line if only `explicit_sabotage` moves.

## Later: EXP-16 Psych-Grounded Cognitive Battery

- Benchmark definition created:
  - `docs/EXP-16_psych_grounded_cognitive_battery.md`
  - `experiments/exp16/generate_tasks.py`
  - `experiments/data/exp16_cognitive_smoke.jsonl`
  - `experiments/data/exp16_cognitive_pilot.jsonl`
- Remaining implementation:
  - write EXP-16 open-model runner after EXP-15 is inspected
  - use the EXP-15 bridge result to finalize condition names
  - add family/task-type/difficulty analysis tables
  - add optional trace metrics for Qwen3/DeepSeek
- Keep insight/creativity out of the first runner. The first benchmark covers
  working memory/updating, inhibition/distractor control, rule switching, and
  novel rule learning.

## Later: EXP-17 Affect-Directional Judgment Tasks

- Add tasks where affect should plausibly change response direction rather than
  objective correctness:
  - ambiguous social interpretation
  - optimism/pessimism judgments
  - risk appraisal
  - mood-congruent continuation choice
- Use these to test whether affect prompts create any aligned behavioral signal
  even when benchmark accuracy remains null.
