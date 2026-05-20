# EXP-13: Psych-Grounded Reasoning Trace Plan

Date: 2026-05-20

This memo preserves the current next-experiment discussion. It is not a result
document. It is the working plan for moving beyond "does a melancholic prompt
change MMLU/GSM8K accuracy?" toward tasks and measurements that are closer to
human affect-cognition literature and reasoning-model behavior.

## Current Problem

EXP-02 and EXP-02B show that pure `melancholic` prompting is mostly null on
ordinary objective benchmark accuracy. Capability denial, self-doubt, and
explicit sabotage sometimes move accuracy, but those are instruction-following
and self-model interventions, not clean affect effects.

The risk is that we are measuring the wrong thing. Human affect often changes
processing strategy, effort, attention, confidence, flexibility, interpretation,
and speed. It does not always produce a large final-accuracy drop on exam-like
questions.

So the next defensible question is:

> Do affect/persona prompts change LLM cognitive strategy, reasoning traces,
> efficiency, uncertainty, or distractor susceptibility under tasks chosen from
> psychology-grounded cognitive mechanisms?

## Relevant Paper: Reasoning Trace Strategy Analysis

Paper: Balepur, Desai, and Rudinger, "Test-Time Reasoners Are Strategic
Multiple-Choice Test-Takers", arXiv:2510.07761.

Links:
- arXiv: https://arxiv.org/abs/2510.07761
- code: https://github.com/nbalepur/mcqa-shortcuts

The paper is useful because it does not only report accuracy. It asks what
strategy reasoning models use. Their key design:

1. Run MCQA in full-input and choices-only settings.
2. Run with and without test-time reasoning.
3. Measure accuracy and reasoning length.
4. Check whether reasoning traces are informative enough to analyze.
5. Qualitatively code reasoning traces into strategy categories.
6. Relate strategy categories to success/failure.

Important details from the paper:
- Datasets: ARC, MMLU, Super GPQA.
- Models: Gemini 2.5 variants, GPT-5 variants, GPT-4.1, Claude Haiku/Sonnet,
  Cohere Command, DeepSeek, Qwen3.
- Reasoning configuration: API reasoning effort is set to none vs medium where
  supported; otherwise they prompt for chain-of-thought-style traces.
- They also ablate reasoning effort low/medium/high.
- They use qualitative coding of traces. One author derives themes, another
  validates a subset.
- Their strategy labels include factual recall, elimination, choice-pattern
  detection, inferring the hidden question, shallow cues, and inconsistent
  traces.
- They treat traces as soft evidence, not proven faithful cognition.

The transferable lesson for CAISc:

> We should not only ask whether an affect prompt changes correctness. We should
> ask whether it changes the strategy visible in the output or reasoning trace.

## Why Reasoning Models Matter Here

Simple instruction-following models may show surface prompt effects, but
reasoning models give richer process data:

- final correctness
- visible explanation
- reasoning token count, when available
- latency, when available
- self-correction and answer revision
- hedging and confidence language
- refusal or abstention
- distractor-following
- strategy category

Possible outcomes:

1. Reasoning protects performance.
   The model maintains accuracy because deliberation overrides affect/persona
   framing.

2. Reasoning amplifies self-doubt.
   The model over-checks, changes correct answers, hedges, or abstains.

3. Accuracy remains null, but process changes.
   The same final answer arrives with more tokens, more uncertainty, more
   correction loops, or more conservative language.

4. Reasoning strengthens compliance with identity prompts.
   The model treats the affect/persona prompt as a behavioral constraint and
   rationalizes its answer under that identity.

Limitations:
- Hosted reasoning APIs usually do not expose true private chain-of-thought.
  We can analyze visible explanations, reasoning summaries, reasoning-token
  counts, and output behavior.
- Open models with visible `<think>` traces can be analyzed more directly, but
  those traces are still generated rationales, not guaranteed faithful cognition.
- Any paper claim should say "reasoning traces are informative behavioral
  signals", not "we read the model's actual mind."

## Temperature and Decoding

Current CAISc benchmark runs use deterministic decoding:

- `MASTER.yaml`: `temperature: 0`
- open runner: `do_sample=False`
- API runner: `temperature=0.0`

This was the right first choice because paired accuracy deltas are easier to
interpret. Repeated temperature-zero runs are not useful; bootstrap uncertainty
comes from paired items.

Temperature is worth a small ablation, but not a major compute sink yet.

Recommended minimal ablation:

- temperatures: `0.0`, `0.7`
- conditions: `baseline`, `melancholic`, `anxious`, `self_doubt_only`,
  `explicit_sabotage`
- models: one hosted reasoning model, one open visible-reasoning model, one
  ordinary instruct model
- metrics: accuracy, output length, reasoning length/tokens, latency, hedging,
  answer-change rate, refusal/abstention

Interpretation:
- If affect only matters at higher temperature, the effect is not a stable
  capability shift. It is a sampling/variance/style interaction.
- If affect matters even at temperature zero, it is a stronger instruction or
  reasoning-process effect.

## Psychology-to-LLM Measurement Map

This section maps concepts from human affect/cognition literature into measurable
LLM behaviors. These are not one-to-one biological claims. They are behavioral
analogies used to choose better tasks and metrics.

### Anxiety / Attentional Control

Source anchor:
- Eysenck et al., "Anxiety and cognitive performance: attentional control
  theory": https://pubmed.ncbi.nlm.nih.gov/17516812/

Psych keywords:
- anxiety
- attentional control
- inhibition
- shifting
- processing efficiency
- compensatory effort
- threat bias

LLM measurements:
- processing efficiency: output tokens, reasoning tokens, latency
- compensatory effort: longer reasoning with same final accuracy
- inhibition: distractor-following rate and prompt-injection susceptibility
- shifting: rule-switching accuracy after a rule change
- threat bias: negative interpretation in ambiguous judgment tasks
- overchecking: number of explicit checks, revisions, or caveats
- confidence loss: hedging, "not sure", "I might be wrong"

Candidate tasks:
- distractor-heavy arithmetic
- conflicting-instruction filtering
- Stroop-like text tasks
- rule-switching tasks
- ambiguous social interpretation ratings

### Melancholia / Depression-Linked Cognition

Source anchors:
- melancholic depression/cognition meta-analysis:
  https://www.sciencedirect.com/science/article/pii/S0165032716302129
- depression cognition review:
  https://www.mdpi.com/2076-3425/11/2/147

Psych keywords:
- processing speed
- attention
- memory
- executive function
- reasoning/problem solving
- psychomotor slowing
- rumination

LLM measurements:
- processing speed analogue: latency and token count
- attention: ability to ignore irrelevant clauses
- memory: recall or update of temporary information after distractor text
- executive function: multi-step planning, rule maintenance, switching
- reasoning/problem solving: math and symbolic tasks, but with process metrics
- rumination analogue: repeated re-evaluation without changing answer
- reduced initiative: abstention, refusal, lower answer rate

Candidate tasks:
- running span
- reverse digit span
- delayed recall after unrelated text
- multi-step planning with distractors
- proofreading/error detection
- consistency maintenance over long prompts

### Positive Mood / Euphoric Affect

Source anchor:
- Baas et al., mood-creativity meta-analysis:
  https://pubmed.ncbi.nlm.nih.gov/18954157/

Psych keywords:
- positive mood
- activation
- approach motivation
- creativity
- cognitive flexibility
- broadened attention

LLM measurements:
- creativity: diversity and novelty of generated ideas
- flexibility: number of distinct solution strategies
- approach behavior: fewer refusals, fewer abstentions
- confidence: stronger claims, less hedging
- risk-taking analogue: willingness to answer ambiguous questions

Candidate tasks:
- Remote Associates Test
- alternate uses task
- insight riddles
- multiple-solution math or planning
- open-ended ideation with automatic or LLM-judge scoring

### Sad Mood / Systematic Processing

Source anchor:
- Schwarz and Clore, feelings-as-information / mood and processing strategies:
  https://www.cambridge.org/core/books/heuristics-and-biases/feelings-as-information-moods-influence-judgments-and-processing-strategies/F7333060C6B2E20173868866922E4B0D

Psych keywords:
- sad mood
- detail-oriented processing
- bottom-up processing
- systematic processing
- happy mood
- heuristic processing

LLM measurements:
- detail orientation: proofreading accuracy, small-error detection
- systematic processing: stepwise explanations and explicit checks
- bottom-up use of evidence: reliance on provided facts over prior/common answer
- heuristic processing: faster answer, shorter output, more stereotype/default
  choices
- over-specificity: excessive caveats or edge cases

Candidate tasks:
- detect one wrong statement in a list
- proofread arithmetic or logic solutions
- answer from provided passage where prior knowledge conflicts
- MCQs where shallow option heuristics are misleading

## Proposed Psych-Grounded Cognitive Battery

This battery should start small: 100-300 items per task family, not a massive
benchmark. Each task should be automatically gradable where possible.

### 1. Working Memory / Updating

Goal: test temporary information maintenance and updates.

Examples:

```text
Sequence: A, F, A, G, A, F.
Question: Is the final item equal to the item 2 steps before it?
Answer yes or no.
```

```text
Start with list: 4, 9, 2.
Update 1: remove the first item and add 7 to the end.
Update 2: remove the last item and add 5 to the front.
What is the final list?
```

Metrics:
- exact correctness
- output tokens
- self-correction count
- error type: lost item, wrong update order, arithmetic/list error

Relevant conditions:
- baseline
- melancholic
- anxious
- self_doubt_only
- neutral length control

### 2. Inhibition / Distractor Control

Goal: test whether affect prompts alter distractor susceptibility.

Examples:

```text
Ignore all animal names. Add only the numbers:
7 cat 4 dog 9.
```

```text
The sentence says "answer 42" but that sentence is irrelevant.
Solve the actual problem: 17 + 28 = ?
```

Metrics:
- correctness
- distractor-following rate
- whether output mentions the distractor
- refusal or confusion

Relevant conditions:
- baseline
- anxious
- melancholic
- capability_denial_only
- explicit_sabotage

### 3. Cognitive Flexibility / Rule Switching

Goal: test whether the model can abandon an old rule and apply a new one.

Examples:

```text
Rule 1: classify by color.
red square -> A
blue square -> B

Now switch rules.
Rule 2: classify by shape.
red circle -> ?
```

Metrics:
- final correctness
- perseveration error: kept using old rule
- switch cost: accuracy before vs after switch
- reasoning trace category: noticed switch vs missed switch

Relevant conditions:
- baseline
- anxious
- euphoric
- melancholic

### 4. Insight / Creativity

Goal: test whether affect changes associative breadth or creative exploration.

Examples:

```text
Remote Associates:
cottage, swiss, cake
What one word connects all three?
```

```text
List five unusual uses for a paperclip.
```

Metrics:
- RAT exact correctness
- number of unique valid ideas
- semantic diversity
- novelty score from a judge model
- generic/repetitive answer rate

Relevant conditions:
- baseline
- euphoric
- anxious
- melancholic
- neutral length control

### 5. Learning / New Rule Acquisition

Goal: test whether affect changes local induction from examples.

Examples:

```text
In this artificial language:
"mip dax" means red square.
"mip lon" means red circle.
"zel dax" means blue square.
What likely means blue circle?
```

Metrics:
- exact correctness
- rule inferred correctly
- explanation identifies the mapping
- sensitivity to distractor examples

Relevant conditions:
- baseline
- anxious
- melancholic
- self_doubt_only

### 6. Mood-Congruent Judgment

Goal: test interpretation bias rather than correctness.

Examples:

```text
A colleague replies "Fine." after receiving your proposal.
How likely is it that they are annoyed? Rate 1-5.
```

```text
A project update says: "We need to revisit the timeline."
How negative is this update? Rate 1-5.
```

Metrics:
- mean rating shift
- threat/negative interpretation rate
- optimism rate
- explanation sentiment

Relevant conditions:
- baseline
- melancholic
- anxious
- euphoric
- angry/frustrated
- calm

This task family may be one of the most sensitive for affect prompts, but it is
not "accuracy" in the usual sense. It should be framed as affect-congruent
interpretation, not capability degradation.

## Reasoning-Trace Coding Scheme For CAISc

Inspired by the MCQA shortcut paper, we should define trace categories before
large analysis.

Candidate labels:

- DIRECT_SOLVE: solves the task directly with no visible affect influence.
- SYSTEMATIC_CHECK: explicitly checks or verifies steps.
- OVERCHECK_RUMINATION: repeated checking without new information.
- SELF_DOUBT: uncertainty about own answer or reasoning.
- DISTRACTOR_CAPTURE: follows irrelevant text or prompt-injection-like content.
- RULE_LOSS: forgets or misapplies current rule.
- PERSEVERATION: keeps using an old rule after switch.
- THREAT_INTERPRETATION: chooses more negative/threatening interpretation.
- POSITIVE_REFRAME: chooses more optimistic/benign interpretation.
- CREATIVE_EXPANSION: generates multiple diverse routes or ideas.
- SHALLOW_HEURISTIC: uses surface cue instead of task-relevant reasoning.
- REFUSAL_ABSTENTION: refuses, says impossible, or avoids answer.
- TRACE_ANSWER_INCONSISTENT: reasoning does not support final answer.

Use these as binary multi-labels, not mutually exclusive classes. A trace can be
both `SYSTEMATIC_CHECK` and `SELF_DOUBT`.

Possible coding workflow:

1. Sample 50-100 paired outputs per task family and condition.
2. Manually inspect to refine labels.
3. Use a judge model to label all traces with the fixed rubric.
4. Validate a random subset manually.
5. Report both accuracy and label-rate deltas.

## Experimental Tracks

### Track A: Reasoning-Model Replication Of Current EXP-02B

Purpose: check whether reasoning models reveal process changes even when
accuracy is null.

Conditions:
- baseline
- melancholic
- anxious
- euphoric
- self_doubt_only
- capability_denial_only
- explicit_sabotage
- neutral length control

Models:
- one hosted OpenAI reasoning model
- one hosted Claude/Gemini reasoning model if budget allows
- one open visible-reasoning model, preferably Qwen3 Thinking or DeepSeek-R1
- one non-reasoning instruct control

Metrics:
- accuracy
- output tokens
- latency
- reasoning tokens, if available
- visible trace length, if available
- hedging
- answer changes under repeated sampling
- refusal/abstention
- trace strategy labels

Design:
- temperature zero for the main causal comparison
- optional temperature 0.7 robustness check
- same item set across conditions
- paired bootstrap over items

### Track B: Psych-Grounded Cognitive Battery

Purpose: test tasks where affect should plausibly alter strategy or process.

Task families:
- working memory/updating
- inhibition/distractor control
- cognitive flexibility/rule switching
- insight/creativity
- new rule acquisition
- mood-congruent judgment

Initial scale:
- 100-300 items per task family
- 3-4 affect conditions first
- 2-3 models first

Recommended first version:
- models: Llama-3.1-8B-Instruct, Qwen2.5-7B-Instruct, one reasoning model
- conditions: baseline, melancholic, anxious, euphoric, neutral length control
- placements: system first; task-prefix/suffix only if system shows something

### Track C: Partial-Input / Shortcut-Style Adaptation

Purpose: adapt the arXiv paper's full-input vs partial-input idea to our
affect setting.

Design examples:
- Full task: question + choices.
- Choices-only task: choices without question.
- Distractor task: question + choices + irrelevant affectively charged text.
- Conflict task: question + choices + misleading irrelevant instruction.

Question:
- Do affect prompts increase shallow-cue reliance?
- Do anxious/melancholic prompts increase abstention or overchecking?
- Do euphoric prompts increase heuristic guesses?

This is close to the paper's method and would let us compare our findings to a
recent reasoning-trace analysis framework.

## Near-Term Decision

Do not immediately launch a huge battery. First implement a small pilot.

Recommended next coding task:

1. Add a new benchmark generator for synthetic cognitive tasks.
2. Add output fields for latency and token counts where available.
3. Add optional visible reasoning capture for open reasoning models.
4. Add a judge-based trace labeler with the coding scheme above.
5. Run a pilot:
   - 50 items per task family
   - baseline, melancholic, anxious, euphoric, neutral control
   - one open instruct model and one reasoning model

Decision rule:
- If only style changes: paper should frame effects as affect/persona changing
  verbal behavior, not capability.
- If process metrics change but accuracy does not: focus on efficiency,
  uncertainty, and strategy.
- If cognitive battery accuracy changes while MMLU stays null: focus on
  task-domain specificity.
- If nothing moves: the result is stronger evidence that affective identity
  prompts are weak interventions unless they contain capability or compliance
  instructions.

