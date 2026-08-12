# Inclusive CODS results: interpretation memo

## Analysis decision

The primary analysis includes **every structurally complete canonical cell**:
24 factorial cells and six surface-robustness cells, totaling **423,600 model
responses**. Diagnostic parse/truncation thresholds and mixed token budgets are
retained as annotations, not used as post-hoc deletion rules. In particular,
all four Llama cells and the two mixed-budget seed-16061 cells remain in the
reported aggregates. This is an inclusive analysis, not a claim that the
diagnostics are irrelevant.

Accuracy and paired effects are equally weighted over seed--family cells,
matching Equation 1 in the paper. Confidence intervals resample tasks within
each of the 32 seed--family strata and retain the complete paired prompt
factorial for every sampled task.

## The paper's central answer

**Self-doubt language is not a generally useful correction instruction. Its
increment after direct checking is strongly model-, task-, and context-dependent.**

Across the six checkpoints, overall CDE ranges from **-1.43 to +2.59 percentage
points**. Three checkpoint estimates are positive and three are negative. The
effects are statistically separated from zero for Qwen (-1.43 pp), Llama
(-0.92 pp), Phi (+2.59 pp), Tulu-SFT (+1.04 pp), and Tulu-DPO (+1.51 pp), while
Mistral is indistinguishable from zero (-0.47 pp). This immediately rules out a
single cross-model claim that anthropomorphic doubt either helps or harms.

These intervals quantify paired task uncertainty conditional on the four frozen
generator seeds. Seed ranges and directions are reported separately; the paper
must not describe a narrow task-bootstrap interval as population-level certainty
over all possible task generators.

The more interesting regularity is contextual. Under a minimal task request,
four of six checkpoints have positive CDE. Once the task already asks for
reasoning, only two remain positive. The largest switches are:

- **Phi:** +5.31 pp under the minimal request but -0.14 pp when reasoning is
  already requested (CM -5.45 pp).
- **Qwen:** +0.58 pp under the minimal request but -3.44 pp when reasoning is
  already requested (CM -4.02 pp).
- **Tulu-DPO:** +2.52 pp under the minimal request and only +0.50 pp with the
  reasoning request (CM -2.02 pp).

This supports a **conditional policy-elicitation account**: doubt language can
change execution when a behavioral policy is under-specified, but often adds
nothing—or actively interferes—once the task already elicits deliberation.
Because we do not observe internal computation, the paper should say
"consistent with policy elicitation," not claim a hidden psychological state.

## Exact model-level scorecard

All effects below are percentage points. CDE averages the minimal and
reasoning-requested task contexts.

| Checkpoint | Neutral | Self-doubt gain | Checking gain | CDE | CDE minimal | CDE reasoning | CM | Concision effect |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen 2.5 7B | 66.44 | +4.83 | +7.70 | **-1.43** | +0.58 | -3.44 | -4.02 | -27.05 |
| Mistral 7B | 24.96 | -1.71 | +0.51 | -0.47 | -0.09 | -0.84 | -0.75 | +1.10 |
| Llama 3.1 8B | 20.00 | -0.59 | +1.45 | **-0.92** | -1.58 | -0.27 | +1.31 | -5.63 |
| Phi 3.5 Mini | 44.98 | -0.36 | +0.45 | **+2.59** | +5.31 | -0.14 | -5.45 | -7.53 |
| Tulu 3 SFT 8B | 13.52 | +0.64 | -0.12 | **+1.04** | +1.13 | +0.95 | -0.17 | +1.32 |
| Tulu 3 DPO 8B | 16.30 | +1.88 | +1.79 | **+1.51** | +2.52 | +0.50 | -2.02 | -3.74 |

The main text should foreground CDE, its context decomposition, and paired
uncertainty. Neutral accuracy is necessary context, but this is not an ability
leaderboard: a low-neutral-accuracy checkpoint can still have an informative
paired treatment effect.

## Direct checking is useful only conditionally

Direct checking has a very large overall gain for Qwen (**+7.70 pp**) but not a
general cross-model benefit. The other five checkpoint estimates range from
-0.12 to +1.79 pp; Mistral and Phi intervals include zero. The honest claim is:

> Direct checking can be an effective intervention, most clearly for Qwen, but
> neither checking nor self-doubt is a universally transferable prompt policy.

For Qwen the mechanism is especially clear. Under a minimal request, checking
raises accuracy by about 15 points on the held-out surface subset, while the
increment of doubt after checking is small. Under an explicit reasoning request,
the checking gain shrinks and doubt becomes harmful. This is the best motivating
example for the introduction and the first paragraph of Results.

## Task-family heterogeneity is substantive, not noise

Model averages hide large, reproducible task-family reversals. Family CDEs span
approximately **-8.4 to +8.9 pp**:

- Qwen: rule switching -8.1 pp, but novel-rule learning +2.1 pp.
- Mistral: working memory +4.2 pp, but relational integration -5.4 pp.
- Llama: error monitoring +5.1 pp, but novel-rule learning -8.4 pp.
- Phi: positive on working memory (+6.1), inhibition (+6.5), and rule switching
  (+6.2), but negative on planning (-1.9).
- Tulu-SFT: novel-rule learning +8.9 pp, but goal management -4.8 pp.
- Tulu-DPO: working memory +5.1 and inhibition +6.1 pp, but novel-rule learning
  -2.4 pp.

Twenty-one nonzero model--family directions retain their sign across all four
task seeds. This is strong evidence that the heterogeneity is not merely a
favorable random seed. It also shows why one-domain public benchmarks are
insufficient for prompt-attribution claims.

Difficulty is a moderator for several checkpoints. For Phi, CDE rises from
+0.82 pp on easy tasks to +4.49 pp on hard tasks; for Tulu-SFT it rises from
-0.39 to +2.73 pp. This should be presented as descriptive heterogeneity, not a
monotonic law, because Mistral and Qwen do not share the same trend.

## Concision reveals a format--computation tradeoff

The `check + concise` condition sharply reduces output length, but often at a
large accuracy cost. Across the 12 model--context cells, the median token
change is **-85.4 generated tokens** and the median accuracy change is **-3.74
pp**. The extreme case is Qwen under the minimal request: the condition removes
about 175 tokens and costs almost 40 accuracy points. In contrast, Tulu-SFT and
some Mistral cells become slightly more accurate while emitting fewer tokens.

The interpretation must remain behavioral: prohibiting visible steps can alter
task performance, but token length is not direct evidence of hidden reasoning.
This result motivates reporting accuracy and format compliance jointly rather
than treating concise outputs as automatically better.

## Surface robustness: broad patterns survive, exact effects move

On 330 paired latent tasks rendered canonically, structurally, and as scenarios,
the mean three-way correctness agreement is **81.3%** across model--prompt--context
cells. However, the median absolute shift in CDE relative to the canonical form
is **1.52 pp**, and only seven of the 12 model--context CDE signs are invariant
over all three renderings.

The robust conclusions are therefore coarse rather than exact:

- Qwen remains positive under the minimal request and negative when reasoning
  is requested in all three surface forms.
- Mistral also preserves the same context-dependent signs across all forms.
- Tulu-SFT preserves a positive minimal-context CDE.
- Llama, Phi, and Tulu-DPO exhibit at least one near-zero sign crossing.

This result is useful, not embarrassing: answer-preserving wording variation is
a genuine source of uncertainty. Report it as a boundary on claims about exact
effect size and use it to justify the paired surface instrument.

## Diagnostics and protocol sensitivity

Excluding the mixed-budget seed changes overall CDE by only **+0.02 pp for
Qwen** and **-0.13 pp for Llama**. The inclusive conclusions are therefore not
being driven by the two 384/768-token composites.

A separate diagnostic recomputation retains only task pairs in which both
`check` and `doubt + check` produced parsed, non-truncated responses. It is not
the primary estimator—dropping outcomes after observing response completion can
be selective—but it identifies where generation failures matter. For five
checkpoints the context-specific shift is at most 0.47 pp. Llama is the
exception: retaining 86.7% of minimal pairs moves CDE from -1.58 to -0.60 pp,
and retaining 82.5% of reasoning-requested pairs moves it from -0.27 to +1.15
pp. Therefore:

- Qwen, Phi, and both Tulu context patterns are not explained by diagnostic
  failures.
- The exact Llama effect, especially in the reasoning-requested context, is
  completion-sensitive and should be labelled accordingly rather than used as a
  headline replication.

The full checks are in `mixed_budget_protocol_sensitivity.csv` and
`paired_diagnostic_sensitivity.csv`.

## Post-training case study: DPO changes the profile, not just the level

Relative to Tulu-SFT, Tulu-DPO has +2.78 pp neutral accuracy, +1.91 pp checking
gain, and +0.47 pp overall CDE. The average hides a context interaction: DPO
increases minimal-context CDE by **+1.39 pp** but decreases reasoning-context
CDE by **-0.45 pp**. It also changes the concision effect by -5.06 pp.

The defensible claim is:

> Within the Tulu/Llama-3.1 lineage, post-training changes prompt sensitivity
> and context modulation, not merely baseline competence.

Do not present two Tulu checkpoints as two independent foundation-family
replications, and do not infer a universal effect of DPO from one lineage.

## How to structure the CODS story

1. **Problem:** self-doubt prompts conflate anthropomorphic framing with the
   ordinary instruction to check. Existing unpaired benchmark comparisons
   cannot attribute an observed gain.
2. **Instrument:** DoubtBench/PAIR-CTRL holds task and checkpoint fixed and
   crosses five prompt conditions with two task contexts across 6,400 fresh
   exact-answer tasks.
3. **Primary result:** CDE is not universal (three positive, three negative),
   and task context produces large reversals.
4. **Scientific value:** task families and surface forms expose where a prompt
   effect does and does not transport.
5. **Engineering implication:** use direct behavioral instructions when they
   demonstrably help; do not assume emotional/self-doubt framing is a portable
   correction mechanism.

## Claims to avoid

- Do not say models "experience" doubt.
- Do not say direct checking always helps.
- Do not collapse the six checkpoints into six independent model families.
- Do not call a narrow pooled interval evidence of universal robustness when
  surface signs or task-family effects reverse.
- Do not hide the six diagnostic-flagged cells; report inclusive results and a
  protocol sensitivity table in the appendix.
- Do not interpret output length as hidden reasoning quantity.

## Reproduction

From the repository root:

```bash
python scripts/analyze_cods_inclusive.py
python submissions/cods2026/paper/make_results_figures.py
```

Machine-readable tables and the analysis summary are in this directory. The
figures are in `submissions/cods2026/paper/figures/results/`.
