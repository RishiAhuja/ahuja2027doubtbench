# CODS 2026 paper completion checklist

Deadline checked on 2026-08-08: **August 13, 2026, Anywhere on Earth**.
The current PDF is eight pages total, with references beginning on page 8.

## Definition of done

The submission is done only when:

- [ ] The paper makes one primary contribution: PAIR-CTRL, a validated
  cognitive-control battery plus a common-prefix paired factorial for identifying
  prompt-induced policy changes.
- [ ] Every headline number is regenerated from frozen, quality-checked outputs.
- [ ] Results cover at least four independent foundation families; Tulu-SFT and
  Tulu-DPO are correctly described as checkpoints of the Llama family.
- [ ] Results are reported per model and per seed before any pooled estimate.
- [ ] The paper states the real discovery chronology and does not portray the
  synthetic battery or GSM8K as preregistered confirmation.
- [ ] The final anonymous PDF builds cleanly, fits the CODS limit, and contains no
  credentials, author metadata, hidden comments, or unsupported claims.

## P0: Freeze the paper's claim and scope

- [ ] Use this central question throughout: **Does self-doubt itself help, or does
  the prompt merely cause the model to check its work?**
- [ ] Use the primary contribution statement consistently:
  - PAIR-CTRL is a procedurally generated cognitive-control benchmark with a
    paired counterfactual prompt protocol.
  - The factorial separates self-doubt, direct checking, reasoning elicitation,
    and output constraints while holding the helpful prefix and task fixed.
- [ ] Freeze the three research questions:
  1. Does pure self-doubt add accuracy beyond direct checking?
  2. Does task-level reasoning elicitation moderate that effect?
  3. How do those effects vary across foundation families and post-training
     checkpoints?
- [ ] Scope the benchmark construct as **prompt-induced cognitive-control
  behavior in LLMs**, not human cognition, emotion, or general intelligence.
- [ ] Describe Llama/Tulu as a within-family post-training case study; do not claim
  universal post-training resistance.
- [ ] Make the paper independent of new paid API calls.
- [ ] Move existing proprietary-API results out of the headline evidence; retain
  them only in an appendix if their raw outputs and configurations are auditable.

## P0: Finish and validate the running EXP-18 campaign

### Initial task seed

- [x] Qwen2.5 smoke and full run completed (`26383`, `26384`).
- [x] Mistral corrected smoke and full run completed (`26397`, `26398`).
- [x] Llama smoke and full run completed (`26402`, `26403`).
- [x] Tulu-DPO smoke passed (`26420`).
- [x] Tulu-DPO full run completed successfully (`26421`).
- [x] Tulu-SFT smoke passed (`26405`).
- [x] Tulu-SFT full run completed successfully (`26406`).
- [x] Phi-3.5 smoke rerun passed (`26475`, 200/200 rows, zero parse failures and
  zero truncations; original `26422` exposed an incompatible
  repository-side Transformers cache API; native Phi-3 support is now used).
- [ ] Phi-3.5 full run completes (`26699`; original `26423` was
  dependency-cancelled).

### Independent procedural seeds 16101 and 16102

- [ ] Qwen focused replications rerun (`26669`, `26673`; original `26424`
  lacked a remote data file and `26425` was dependency-cancelled).
- [ ] Mistral focused replications rerun (`26677`, `26681`).
- [ ] Tulu-DPO focused replications rerun (`26685`, `26686`).
- [ ] Llama focused replications rerun (`26706`, `26710`).
- [ ] Tulu-SFT focused replications rerun (`26722`, `26723`).
- [ ] Phi-3.5 initial and focused replication reruns complete (`26699`, `26714`,
  `26718`; smoke `26475` is complete).

### Expanded PAIR-CTRL inventory and evaluation

- [x] Generate and validate 400-task flexibility/rule-learning extensions for
  seeds 16061, 16101, and 16102 (200 tasks per added family per seed).
- [x] Generate and validate an 800-task all-family candidate held-out split,
  seed 19003.
- [x] Confirm all four generated files have unique IDs, frozen manifests,
  SHA-256 hashes, exact family/type/difficulty counts, and self-scoring golds.
- [x] Build three explicit 800-task historical full-split files by combining the
  predecessor tasks and new family extensions; validate 3,200 globally unique
  task IDs across the four full splits.
- [x] Add monitoring/error-detection and constrained-planning families, with
  eight new task types and 400 additional tasks per split.
- [x] Build and structurally validate four 1,200-task candidate splits: six
  families, 25 task types, and 4,800 globally unique task IDs.
- [x] Independently reconstruct the gold answers for all 1,600 newly generated
  monitoring/planning tasks using a separate audit implementation.
- [x] Add relational-integration and goal-management families, bringing the
  candidate core to eight families, 33 task types, 1,600 tasks per split, and
  6,400 globally unique latent tasks.
- [x] Independently reconstruct all 1,600 relational/goal-management golds.
- [x] Generate a held-out wording-robustness layer with structured and
  scenario-framed variants for ten latent tasks per type (660 variants; 99
  canonical/structured/scenario type--surface combinations).
- [ ] Complete the primary 1,600-task held-out core on Qwen (`26650`--`26652`).
- [ ] Complete the primary 1,600-task held-out core on Mistral
  (`26653`--`26655`).
- [ ] Complete the primary 1,600-task held-out core on Llama (`26687`--`26689`).
- [ ] Complete the primary 1,600-task held-out core on Phi (`26690`--`26692`).
- [ ] Complete four-model surface robustness (`26656`, `26657`, `26693`,
  `26694`).
- [ ] Complete seed 16061 with the corrected 768-token budget: Qwen
  (`26658`--`26661`), Mistral (`26662`--`26665`), Llama
  (`26695`--`26698`), and Phi (`26699`--`26702`).
- [ ] Complete Tulu-DPO and Tulu-SFT held-out/extension case studies
  (`26666`--`26668`, `26703`--`26705`).
- [ ] Complete all seed-16101/16102 tails for Qwen (`26669`--`26676`), Mistral
  (`26677`--`26684`), Llama (`26706`--`26713`), and Phi
  (`26714`--`26721`).

### Quality gate for every completed run

- [ ] Every run has exactly ten times its task-file row count: 4,000 rows for a
  400-task component, 8,000 for an 800-task base, and 6,600 for a 660-variant
  surface file.
- [x] Exclude 384-token diagnostics `26474` and `26477` from confirmatory
  analysis; `26474` exposed 16.25--24% truncation in four non-concise
  reasoning-requested cells, and `26477` was stopped after the same budget flaw
  was identified.
- [ ] Confirm the replacement 768-token jobs satisfy the 2% truncation and parse
  gates before merging any result table.
- [ ] Every shared task has all ten cells: five conditions by two task templates.
- [ ] Parse failures are at most 2% globally and are also reported by cell.
- [ ] Truncation is at most 2% globally and is also reported by cell.
- [ ] Model repository, exact revision, tokenizer, generation parameters, task-file
  hash, and code revision are recorded.
- [ ] Raw output, parsed answer, gold answer, token counts, and error flags are
  retained for every row.
- [ ] Failed quality cells are excluded by a declared rule, never silently repaired
  or selectively retained.

## P0: Make PAIR-CTRL benchmark-ready

### Define and freeze version 1

- [ ] Write a benchmark card defining the construct, intended uses, non-uses,
  families, task types, generation process, scoring, and limitations.
- [ ] Decide the final v1 inventory before inspecting new held-out results.
- [ ] Restore all four implemented families:
  - working memory/updating;
  - inhibition/distractor control;
  - cognitive flexibility/rule switching;
  - novel rule learning.
- [ ] Include or explicitly account for all 17 implemented task types; do not keep
  only the nine favorable working-memory/inhibition types without justification.
- [ ] Freeze task templates, difficulty parameters, prompt conditions, primary
  contrasts, scorers, and exclusion thresholds.
- [ ] Create a versioned manifest containing task counts and SHA-256 hashes.

### Gold-answer and instance validation

- [ ] Implement independent answer reconstruction for every task type rather than
  only checking that the stored gold answer scores itself.
- [ ] Add property tests for generator invariants and scorer round trips.
- [ ] Detect exact duplicates and equivalent instances within and across seeds.
- [ ] Audit a stratified sample covering every family, task type, difficulty, and
  answer format.
- [ ] Record ambiguous or invalid items in an exclusion ledger with reasons.
- [ ] Verify that task instructions do not accidentally contain treatment language
  such as uncertainty, checking, emotion, or capability statements.

### Fresh confirmation

- [ ] Generate at least one genuinely new seed only after the v1 design and
  analysis plan are frozen.
- [ ] Do not use the fresh seed for prompt development, threshold selection, or
  task-template revision.
- [ ] Run the frozen factorial on the fresh seed using one checkpoint from each of
  the four foundation families; extend to all six checkpoints if time permits.
- [ ] Label seeds 16001/16101/16102 as development/replication rather than claiming
  they were untouched held-out confirmation.

### Difficulty and reliability analysis

- [ ] Report accuracy by family, task type, difficulty, model, and seed.
- [ ] Check whether easy/medium/hard generally produces monotonic difficulty.
- [ ] Flag ceiling and floor task types.
- [ ] Report seed-to-seed effect consistency and benchmark reliability.
- [ ] Run a small task-wording paraphrase study to identify template-specific
  effects.

## P0: Prompt construct audit without new API cost

- [x] Twelve affect candidates were evaluated by three development judges.
- [x] Selected prompts were evaluated by two held-out proprietary judges.
- [x] Rule-based capability and task-directive checks exist.
- [ ] Add one local open-model held-out audit for provider/family diversity; do not
  justify it merely as making the judge count equal six.
- [ ] Report development and held-out judges separately.
- [ ] Preserve all judge prompts, raw outputs, parsing failures, and aggregation
  rules.
- [ ] State that the audit validates prompt wording, not that all target models
  interpret the prompts identically.

## P0: External/convergent validation

- [ ] Select a small public benchmark subset aligned with PAIR-CTRL constructs, such as
  state tracking, shuffled-object tracking, rule switching, logical deduction,
  distractor filtering, or sequence manipulation.
- [ ] Freeze the public tasks and scorers before running prompt conditions.
- [ ] Use the same common prefix, five conditions, task-template contrast, decoding,
  and quality gates as the synthetic battery wherever possible.
- [ ] Evaluate at least one representative checkpoint from Qwen, Mistral,
  Llama/Tulu, and Phi families.
- [ ] Compare interaction directions, not just raw accuracy, between PAIR-CTRL
  and public tasks.
- [ ] Keep GSM8K as a domain-shift/supporting result.
- [ ] Do not claim that GSM8K alone identifies reasoning elicitation: it changes
  both domain and task instructions relative to PAIR-CTRL.

## P0: Statistical analysis and result lock

- [ ] Define the primary contrasts before opening fresh-seed outputs:
  - pure self-doubt minus neutral;
  - direct checking minus neutral;
  - self-doubt plus checking minus direct checking;
  - self-doubt plus checking minus pure self-doubt;
  - checking plus concision minus checking.
- [ ] Compute every contrast separately for minimal and reasoning-requested tasks.
- [ ] Compute the template interaction as a paired difference-in-differences.
- [ ] Report paired wins, losses, and ties in addition to accuracy deltas.
- [ ] Use paired bootstrap intervals over shared task IDs with a frozen seed and
  resample count.
- [ ] Report each procedural seed separately before pooling.
- [ ] Limit confirmatory inference to the frozen contrasts; label all further slices
  exploratory.
- [ ] Produce family/task-type/difficulty analyses without selecting only favorable
  cells.
- [ ] Create one machine-readable evidence ledger mapping every paper claim to its
  exact output files and analysis command.
- [ ] Freeze final result CSV/JSON files before regenerating tables and figures.

## P0: Rewrite the paper around one coherent contribution

### Title and abstract

- [ ] Use a title centered on the battery and deconfounding question, e.g.
  **Self-Doubt or Just Checking? A Paired Cognitive-Control Benchmark for
  Deconfounding Identity Prompts**.
- [ ] Rewrite the abstract only after the final result lock.
- [ ] State six checkpoints but four foundation families accurately.
- [ ] Do not use universal language such as “LLMs” when the evidence supports only
  the tested families and versions.

### Introduction

- [ ] State the contamination problem and the self-doubt-versus-checking question.
- [ ] Introduce PAIR-CTRL and the paired factorial as the solution.
- [ ] State one primary contribution and at most two supporting contributions.
- [ ] Give the honest chronology: generic benchmark results motivated the targeted
  battery, and the battery results motivated EXP-18.
- [ ] Replace the old teaser with a benchmark/factorial/outcome diagram generated
  from frozen concepts and final results.

### Related work

- [ ] Cover emotional/identity prompting, metacognitive/checking prompts, prompt
  sensitivity, synthetic evaluation, cognitive-control benchmarks, and paired
  counterfactual evaluation.
- [ ] Explain precisely how PAIR-CTRL differs from GSM8K, MMLU, BIG-Bench/BBH,
  and prior emotion-prompt evaluations.
- [ ] Verify every citation against the original paper.

### Benchmark and experimental design

- [ ] Describe all eight families, 33 task types, generation, difficulty, and
  independent validation.
- [ ] Show the frozen common prefix and all condition components.
- [ ] Explain why checkpoints and foundation families are counted separately.
- [ ] Explain pairing, seed generation, decoding, scoring, quality gates, and
  statistical estimands.
- [ ] Mark discovery, replication, held-out, supporting, exploratory, and excluded
  evidence explicitly.

### Results

- [ ] Lead with the common-prefix factorial, not the chronology of old experiments.
- [ ] Report the self-doubt increment beyond checking as the central result.
- [ ] Report task-template interactions on identical tasks.
- [ ] Report heterogeneity across the four foundation families.
- [ ] Report benchmark-family and difficulty behavior.
- [ ] Present public-task/GSM8K results as external checks.
- [ ] Present Llama/Tulu as a scoped post-training case study.
- [ ] Ensure prose, abstract, teaser, figures, tables, and appendix use identical
  frozen values.

### Discussion and limitations

- [ ] Distinguish observable response policies from internal emotion or cognition.
- [ ] Discuss post-hoc battery development and the role of the fresh held-out seed.
- [ ] Discuss procedural-template artifacts and public-task transport.
- [ ] State that four tested families do not establish a universal model law.
- [ ] Avoid claiming that output length itself causally produces correctness.

## P1: Figures, tables, and appendix

- [ ] Teaser: battery families -> factorial interventions -> model/task-dependent
  outcomes.
- [ ] Benchmark table: eight families, 33 task types, counts, answer types, and
  difficulty parameters.
- [ ] Main result figure: primary paired contrasts by model family with intervals.
- [ ] Interaction figure: minimal versus reasoning-requested contrast on identical
  tasks.
- [ ] Robustness figure/table: per-seed and fresh-held-out estimates.
- [ ] External-validation figure: aligned public tasks versus PAIR-CTRL.
- [ ] Post-training table: Llama/Tulu case study, explicitly scoped.
- [ ] Move full cell tables, task examples, prompt strings, scorer audit, and
  exploratory analyses to the appendix/artifact.
- [ ] Give every figure an informative caption and accessibility description.

## P1: Reproducibility package

- [ ] Synchronize completed HPC outputs into stable local result directories.
- [ ] Record model revisions and licenses.
- [ ] Include task-generation, validation, scoring, analysis, and figure scripts.
- [ ] Include environment/requirements and exact reproduction commands.
- [ ] Ensure scripts regenerate tables and figures from frozen result files.
- [ ] Remove passwords, tokens, usernames where unnecessary, cache paths, and other
  credentials from the repository and artifacts.
- [ ] Prepare an anonymous artifact archive or repository link if permitted.
- [ ] Add a benchmark data card/model-use statement and responsible-use section.

## P2: Do only if the central package is already complete

- [ ] Cross-family base-versus-instruct post-training study with comparable prompt
  serialization and an adherence canary.
- [ ] Additional public benchmarks beyond one aligned validation suite.
- [ ] Human replication of behavior-judge labels.
- [ ] Corrected MATH rescoring.
- [ ] Reasoning-model reruns with substantially larger budgets.
- [ ] Additional paid API models.

These are not required for the current paper and must not delay the central
benchmark, factorial analysis, or submission.

## Final manuscript and submission checks

- [x] Official ACM `sigconf` template and portable style files are present.
- [x] Current manuscript is double anonymous.
- [ ] Confirm final author list and ordering outside the anonymous manuscript.
- [ ] Declare all conflicts of interest in OpenReview.
- [ ] Rebuild with `latexmk` from a clean state.
- [ ] Resolve undefined citations/references, fatal errors, and material overfull
  boxes.
- [ ] Render and visually inspect every PDF page at readable resolution.
- [ ] Verify fonts, vector figures, table legibility, captions, and grayscale use.
- [ ] Recheck the **8 content pages + up to 2 reference pages** limit after the
  rewrite; do not shrink text or margins to force compliance.
- [ ] Confirm references begin after the body-page limit.
- [ ] Inspect PDF metadata and embedded files for author names or local paths.
- [ ] Spell-check and perform a final number-consistency audit.
- [ ] Confirm title, abstract, keywords, CCS terms, and OpenReview metadata match.
- [ ] Upload early enough to download and inspect the submission-system PDF.
- [ ] Remove anonymity and add rights/conference metadata only for camera-ready.

## Working schedule

### August 8--9: experiments and benchmark freeze

- [ ] Finish current EXP-18 chains and retrieve all outputs.
- [ ] Freeze PAIR-CTRL v1 scope, validation rules, and fresh-seed analysis plan.
- [ ] Implement independent task validation and local open-model prompt audit.
- [ ] Generate the fresh held-out seed and aligned public-task subset.

### August 9--10: final runs and analysis

- [ ] Run fresh-seed and external-validation jobs.
- [ ] Complete quality gates, paired analyses, interactions, and evidence ledger.
- [ ] Lock final tables and figures.

### August 10--11: full rewrite

- [ ] Rewrite the paper around PAIR-CTRL and the common-prefix factorial.
- [ ] Move legacy/discovery material to the appendix or remove it.
- [ ] Regenerate the teaser, figures, and tables.

### August 12: submission freeze

- [ ] Freeze experimental results and manuscript content.
- [ ] Perform reproducibility, anonymity, citation, page-limit, and visual checks.
- [ ] Prepare and inspect the anonymous artifact package.

### August 13: buffer and submit

- [ ] Upload before the deadline buffer, download the submitted PDF, inspect it,
  and complete OpenReview metadata and conflicts.

## Stop rules

- [ ] If an EXP-18 model/seed fails the declared quality gate, report the failure
  and exclude it by rule; do not tune thresholds per model.
- [ ] If results disagree across seeds or families, make heterogeneity the result;
  do not select a favorable subset.
- [ ] If the fresh seed does not reproduce a discovery effect, revise the headline
  claim before submission.
- [ ] If difficulty labels or task mappings fail validation, narrow the benchmark
  claim and document the limitation rather than asserting cognitive validity.
- [ ] If the external suite does not transport, report that boundary condition.
- [ ] If required P0 work cannot be completed cleanly, submit a narrower, honest
  paper rather than filling pages with weak exploratory experiments.
