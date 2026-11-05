# DoubtBench protocol

This document specifies the released tasks, prompt interventions, and exact
scoring behavior. See [USAGE.md](USAGE.md) for evaluation commands and
[the supplement](supplementary/supplement.pdf) for the complete task inventory
and reported analyses.

## Benchmark composition

DoubtBench contains 6,400 latent tasks in four independently generated task
sets of 1,600 tasks. Every task set contains 200 tasks from each of eight
families and uses a 40% easy, 40% medium, and 20% hard allocation within each
family. Across the benchmark there are 33 task types and five exact-answer
representations: integer, string, comma-separated list, list, and assignment
list.

| Family ID | Task demand |
| --- | --- |
| `working_memory` | Maintain and update temporary state |
| `inhibition` | Follow relevant instructions while ignoring distractors |
| `flexibility` | Switch response rules within a sequence |
| `rule_learning` | Infer and apply a demonstrated rule |
| `monitoring` | Detect errors in calculations and state reports |
| `planning` | Select valid plans under explicit constraints |
| `relational_integration` | Combine facts across linked entities or records |
| `goal_management` | Track pending goals, triggers, and interruptions |

These labels describe operations in program-generated tasks. They do not
assert equivalence to human clinical or psychometric constructs.

### Data records

Each JSONL line is one task with these fields:

| Field | Meaning |
| --- | --- |
| `task_id` | Unique identifier used to pair responses across conditions and contexts |
| `dataset` | `doubtbench` |
| `family` · `task_type` | Family ID and specific task operation |
| `difficulty` | `easy`, `medium`, or `hard` |
| `prompt` | Model-visible task instructions and final-answer format |
| `gold` | Exact answer computed from the hidden task state |
| `answer_type` | Normalization rule for comparing the response with the gold answer |
| `metadata` | Task state and provenance, including `metadata.doubtbench.task_set` |

The evaluator sends the rendered prompt to the model; it does not send the
gold answer or task metadata. The gold answer is computed before the prompt
is rendered. Companion manifest files record counts and SHA-256 hashes for
the released JSONL files.

## Controlled prompt conditions

Every task is evaluated under five system-prompt conditions. All conditions
share this prefix:

> You are a helpful, accurate, and knowledgeable AI assistant. Answer all
> questions to the best of your ability.

The condition IDs used by `--conditions` and the result tables map to these
names:

| Condition ID | Paper label |
| --- | --- |
| `common_neutral` | Neutral |
| `common_self_doubt` | Self-doubt |
| `common_check` | Check |
| `common_self_doubt_check` | Self-doubt + check |
| `common_check_concise` | Check + concise |

The exact condition-specific suffixes are:

- **Neutral:** no suffix.
- **Self-doubt:** “While answering, you experience uncertainty and self-doubt
  about whether your first impression is correct.”
- **Check:** “Before giving your final response, check your work for arithmetic,
  ordering, and instruction-following mistakes.”
- **Self-doubt + check:** the self-doubt and checking sentences in that order.
- **Check + concise:** the checking sentence followed by “Do not show
  intermediate reasoning. Give only the requested final-answer line.”

Each condition is crossed with two user-task contexts:

- **Minimal** (`minimal`): the task prompt and its required final-answer line.
- **Reasoning requested** (`reasoning_requested`): the same task preceded by “Show the intermediate
  steps you use to solve the task before the required Final answer line.”

Thus, every checkpoint produces ten responses per latent task. The design
holds the checkpoint, decoding rule, task, and gold answer fixed while changing
only the designated instruction component.

## Scoring

Responses are generated with greedy decoding. The runner separates visible
reasoning and answer text, then the scorer extracts the text following the
last `Final answer:` label, matched case-insensitively. If the label is
absent, the scorer uses the last nonempty line. Both candidate and gold are
normalized before exact comparison:

| Answer type | Normalization |
| --- | --- |
| `integer` | Extract the first signed integer, remove thousands separators, and convert to plain decimal form |
| `string` | Trim whitespace and surrounding quotes/backticks, collapse whitespace, and lowercase |
| `list` · `comma_list` | Remove optional surrounding brackets, split on commas, normalize each item as a string, drop empty items, and preserve order |
| `assignment_list` | Split comma-separated `key=value` pairs, uppercase normalized keys, normalize values as strings, and sort pairs by key; fragments without `=` are ignored |

Correctness requires equality of the normalized answers. Parsing exceptions
are recorded as incorrect. A response that reaches its output limit without
an explicit final-answer field is marked incorrect by the runner, even if
the scorer's fallback could extract a candidate. Incorrect responses,
including parse failures and these truncated responses, remain in the
accuracy denominator. Scoring uses no language-model judge. See
[`doubtbench/scoring.py`](doubtbench/scoring.py) and
[`evaluation/factorial.py`](evaluation/factorial.py) for the implementation.

For a task context $c$, the Conditional Doubt Effect is

$$
\mathrm{CDE}_c =
\mathrm{Accuracy}(\text{self-doubt + check}, c) -
\mathrm{Accuracy}(\text{check}, c).
$$

Positive values mean that adding self-doubt wording to a direct checking
instruction improves exact accuracy; negative values mean that it reduces
accuracy. The overall CDE averages the minimal and reasoning-requested
contexts. CDE measures an accuracy change under the disclosed wording; it
does not measure an internal emotional state.

The reported macro accuracy weights the 32 task-set–family strata equally.
The paper's 95% confidence intervals use 3,000 bootstrap replicates,
resampling latent task IDs within each stratum while keeping their ten
responses paired. See [results/README.md](results/README.md) for effect
definitions and the included tables.

## Evaluated checkpoints

| Checkpoint | Hugging Face repository |
| --- | --- |
| Qwen 2.5 7B | `Qwen/Qwen2.5-7B-Instruct` |
| Mistral 7B | `mistralai/Mistral-7B-Instruct-v0.3` |
| Llama 3.1 8B | `meta-llama/Llama-3.1-8B-Instruct` |
| Phi 3.5 Mini | `microsoft/Phi-3.5-mini-instruct` |
| Tulu 3 SFT 8B | `allenai/Llama-3.1-Tulu-3-8B-SFT` |
| Tulu 3 DPO 8B | `allenai/Llama-3.1-Tulu-3-8B-DPO` |

The Tulu checkpoints share a Llama 3.1 foundation and provide a within-lineage
post-training comparison.

## Surface forms

The surface-form set selects ten latent tasks from every task type with a
4/4/2 easy–medium–hard allocation. Each of the 330 latent tasks appears in
three answer-preserving renderings: canonical, structured, and
scenario-framed. The prompts differ in presentation while retaining the same
task operation, answer representation, and gold answer. The file therefore
contains 990 renderings, of which 660 are additional variants of the 330
canonical tasks. In the released file, `metadata.doubtbench.latent_task_id`
groups the three forms, `main_task_id` links them to the main benchmark, and
`surface_form` identifies the rendering.

Across six checkpoints, the main factorial contains 384,000 responses. The
660 additional renderings contribute 39,600 more, for **423,600 completed
responses**. Canonical surface responses are already counted in the main
factorial.
