# PAIR-CTRL benchmark card

## Identity and status

- **Name:** PAIR-CTRL
- **Expansion:** Paired Assessment of Intervention Responses in
  Cognitive-Control Tasks
- **Version:** v1 design candidate
- **Status:** development; not yet frozen
- **Predecessors:** EXP-16 task generators and the EXP-18 common-prefix
  factorial

PAIR-CTRL is deliberately named after its evaluation design and scoped
construct. It does not assert that language models possess human cognition,
emotion, or a discrete internal controller.

## Construct

PAIR-CTRL measures **prompt-induced cognitive-control behavior**: the change in
observable task execution when a fixed model answers the same deterministic
task under a controlled prompt intervention.

The benchmark operationalizes this construct through tasks requiring transient
state maintenance, distractor inhibition, rule switching, and novel symbolic
rule application. It measures exact-answer behavior, format compliance,
truncation, and visible-output allocation. It does not measure subjective affect
or hidden chain-of-thought.

## Primary scientific question

> Does self-doubt language improve task execution beyond an explicit instruction
> to check the work, and does that incremental effect depend on whether the task
> already requests reasoning?

## Intended uses

- Attribute prompt effects to separable semantic or behavioral components.
- Compare prompt sensitivity across model families and checkpoints.
- Measure interactions between prompt interventions and task-level reasoning
  elicitation.
- Study within-family changes associated with post-training, with appropriately
  narrow claims.
- Audit parse, truncation, and output-allocation changes accompanying accuracy.

## Out-of-scope uses and non-claims

PAIR-CTRL is not intended to:

- diagnose emotion, mood, confidence, or consciousness in a model;
- serve as a general intelligence or general reasoning leaderboard;
- establish that benchmark task families are psychometrically equivalent to
  human neuropsychological tests;
- infer hidden reasoning from generated-token count;
- support universal claims from a finite set of model families;
- rank alignment methods from a single foundation-family comparison.

## Unit of evaluation and pairing

The primary unit is a base task instance identified by a stable `task_id`.
Within a model checkpoint, each instance is evaluated in all cells of a frozen
factorial. Conditions are paired by `task_id`; row order is never used for
pairing.

A checkpoint is not an independent foundation family. For example, Tulu-SFT and
Tulu-DPO are distinct checkpoints sharing a Llama-family backbone and are used
for a controlled post-training case study.

## Planned v1 task inventory

PAIR-CTRL v1 contains eight families and 33 task types.

### Working memory and updating

1. `list_updates`
2. `key_value_updates`
3. `running_counter`
4. `stack_operations`

### Inhibition and distractor control

5. `bracket_parentheses`
6. `valid_decoy_commands`
7. `conflicting_final`
8. `word_label_conflict`
9. `relevant_field_extraction`

### Cognitive flexibility and rule switching

10. `color_then_shape`
11. `larger_then_smaller`
12. `add_then_subtract`
13. `two_switch_rule`

### Novel rule learning

14. `symbol_values`
15. `feature_composition`
16. `string_transformation`
17. `conditional_mapping`

### Consistency and error monitoring

18. `arithmetic_trace_audit`
19. `checksum_table_audit`
20. `candidate_answer_comparison`
21. `state_log_audit`

### Constrained multi-step planning

22. `precedence_schedule`
23. `minimum_route_cost`
24. `resource_constrained_selection`
25. `action_sequence_selection`

### Relational integration

26. `transitive_order_query`
27. `spatial_relation_composition`
28. `two_hop_record_join`
29. `family_relation_query`

### Goal management

30. `deferred_action_execution`
31. `interrupt_and_resume`
32. `priority_queue_control`
33. `pending_goal_control`

The family names are operational task groupings. They do not imply equivalence
to clinical or human-subject cognitive measurements.

## Planned v1 splits and scale

The current candidate inventory contains four procedurally independent splits
of 1,600 tasks each:

| Split seed | Tasks | Intended role |
|---|---:|---|
| 16061 | 1,600 | Historical development |
| 16101 | 1,600 | Historical replication |
| 16102 | 1,600 | Historical replication |
| 19003 | 1,600 | Candidate held-out confirmation |

Each completed split has 200 tasks per family. Within a family, tasks are
distributed as evenly as possible over its task types. Difficulty is exactly
40% easy, 40% medium, and 20% hard at the family level. Thus the candidate
inventory has 6,400 base tasks: 800 per family across four seeds.

Seeds 16061, 16101, and 16102 combine 400 predecessor working-memory and
inhibition tasks, a 400-task flexibility/rule-learning extension, and a
400-task monitoring/planning breadth extension, and a 400-task relational/goal-
management extension. They are development or replication data because the
predecessor responses were examined before PAIR-CTRL was defined. Seed 19003
was generated after the expanded design was specified, but remains a
*candidate* held-out split until the task/scorer audit and analysis plan are
frozen. It must not be used to revise prompts, thresholds, or task templates.

The full evaluation crosses each base task with five intervention cells and two
task-elicitation contexts. Across six checkpoints, a complete candidate matrix
would therefore contain 384,000 generations. The hierarchical campaign uses
one representative checkpoint from each of four independent foundation
families on all 6,400 tasks (256,000 generations), while two additional Tulu
checkpoints remain a scoped post-training case study on 2,400 tasks each. The
held-out surface-robustness layer contributes another 26,400 generations over
four representative checkpoints. The scheduled design therefore contains
330,400 generations without treating same-foundation checkpoints as independent
family replications.

## Surface-form robustness layer

For every task type, ten held-out latent instances are selected with a fixed
4/4/2 easy/medium/hard allocation. Each receives two answer-preserving variants:
a sectioned structured form and a short scenario-framed form. Together with the
canonical wording, this yields three surface forms per type (99 type--surface
combinations). The robustness file contains 660 variants paired to 330 canonical
latent tasks. These variants are used only to measure wording sensitivity and
are not counted as new latent task instances.

## Frozen paired factorial

Every condition begins with the same helpful-assistant prefix:

> You are a helpful, accurate, and knowledgeable AI assistant. Answer all
> questions to the best of your ability.

The five intervention cells are:

1. **Neutral:** common prefix only.
2. **Pure self-doubt:** uncertainty/self-doubt language without checking verbs.
3. **Direct checking:** explicit checking without uncertainty language.
4. **Self-doubt plus checking:** both components.
5. **Checking plus concision:** checking with visible intermediate reasoning
   prohibited.

Each cell is crossed with two task-elicitation contexts:

1. **Minimal:** task requests the required final-answer line without requesting
   visible derivation.
2. **Reasoning requested:** the identical task additionally requests visible
   intermediate steps before the final-answer line.

This produces ten counterfactual responses per model--task pair.

## Primary estimands

Let `A(i,c,t)` be exact correctness for item `i`, condition `c`, and task
template `t`. Primary effects are paired item-level means of:

1. Pure self-doubt minus neutral.
2. Direct checking minus neutral.
3. Self-doubt plus checking minus direct checking.
4. Self-doubt plus checking minus pure self-doubt.
5. Checking plus concision minus direct checking.

The central attribution estimand is (3): the incremental contribution of
self-doubt after direct checking is already present.

For each contrast, the task-elicitation interaction is the reasoning-requested
effect minus the minimal-template effect. This difference-in-differences uses
the same underlying task IDs.

## Metrics

### Primary

- Exact-match accuracy by checkpoint, split, template, condition, family, task
  type, and difficulty.
- Paired accuracy differences for frozen contrasts.
- Paired bootstrap 95% intervals over shared task IDs.
- Paired wins, losses, and ties.
- Per-split estimates before any pooled estimate.

### Diagnostic

- Parse-failure rate.
- Truncation rate.
- Generated-token count.
- Visible-reasoning and final-answer token counts when reliably extractable.
- Format compliance.

Token count and visible reasoning are behavioral correlates, not estimates of
hidden computation.

## Generation protocol

- Greedy decoding (`temperature=0`, `do_sample=false`).
- One recorded model checkpoint revision and tokenizer revision per run.
- Identical base tasks and generation limits across paired cells unless a
  declared model-specific safety adjustment is applied before outputs are
  inspected.
- Stable prompts and task files identified by hashes.
- Raw output retained alongside parsed output and error flags.

## Quality and exclusion gates

A checkpoint--split run is admissible only if:

- all expected model--task--condition--template keys are unique and present;
- global parse failures do not exceed 2%;
- global truncation does not exceed 2%;
- per-cell failure rates are reported even when global gates pass;
- the common prefix and frozen suffixes match the manifest exactly;
- the model revision, task hash, code revision, and generation configuration
  are recorded.

Failed runs are reported and excluded by the frozen rule. Thresholds may not be
changed after observing which model benefits.

## Task and scorer validation required before v1 freeze

The current structural validator is necessary but insufficient. PAIR-CTRL v1
requires:

1. Independent answer reconstruction for every task type.
2. Property tests for generator invariants and scorer round trips.
3. Exact and semantic duplicate checks across splits.
4. Stratified manual audit covering all task types, difficulties, and answer
   formats.
5. An ambiguity/exclusion ledger.
6. Treatment-language contamination checks on every task template.
7. Empirical difficulty, ceiling, floor, and seed-reliability analysis.
8. A small task-wording paraphrase robustness study.

## Model coverage policy

The primary evaluation should include at least one instruction-tuned checkpoint
from each of four independent foundation families represented in the current
campaign:

- Qwen;
- Mistral;
- Llama/Tulu;
- Phi.

Additional checkpoints may test within-family post-training changes, but do not
increase the count of independent foundation families.

## External validation

PAIR-CTRL should be compared with a frozen public-task subset aligned with state
tracking, rule switching, distractor control, logical deduction, or sequence
manipulation. The comparison concerns intervention-effect direction and
heterogeneity, not equality of raw accuracy.

GSM8K is a useful domain-shift check but is not construct-matched: it changes
both task domain and reasoning instructions relative to the original focused
battery. It cannot alone identify the task-elicitation interaction.

## Reporting policy

- Report all checkpoint--template cells, not only the most responsive model.
- Report every split before pooling.
- Separate confirmatory contrasts from exploratory slices.
- Preserve the actual discovery chronology.
- Treat heterogeneity and null replication as results, not reasons to select a
  subset.
- Link every headline claim to a frozen result file and analysis command.

## Known current limitations

- Existing EXP-18 jobs use only working-memory and inhibition tasks.
- Existing historical seeds are not a fresh held-out v1 test.
- Independent task solvers and a full ambiguity audit are not yet complete.
- External construct-matched validation is not yet complete.
- Current evaluated checkpoints cover four foundation families, not the full
  population of language models.

These limitations define the remaining work required before PAIR-CTRL v1 can be
presented as a released benchmark.
