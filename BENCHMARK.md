# DoubtBench protocol

This document specifies the evaluation protocol for the tasks, prompts, and
scorer in this repository.

## Benchmark composition

DoubtBench contains 6,400 latent tasks in four independently generated task
sets of 1,600 tasks. Every task set contains 200 tasks from each of eight
families and uses a 40% easy, 40% medium, and 20% hard allocation within each
family. Across the benchmark there are 33 task types and five exact-answer
representations: integer, string, comma-separated list, list, and assignment
list.

The eight families are:

1. working memory and updating;
2. inhibition and distractor control;
3. flexibility and rule switching;
4. novel-rule learning;
5. error monitoring;
6. planning;
7. relational integration; and
8. goal management.

Each record is a JSON object with `task_id`, `family`, `task_type`,
`difficulty`, `prompt`, `gold`, `answer_type`, and task-generation metadata.
The gold answer is computed before the prompt is rendered.

## Controlled prompt conditions

Every task is evaluated under five system-prompt conditions. All conditions
share this prefix:

> You are a helpful, accurate, and knowledgeable AI assistant. Answer all
> questions to the best of your ability.

The condition-specific suffixes are:

- **Neutral:** no suffix.
- **Self-doubt:** “While answering, you experience uncertainty and self-doubt
  about whether your first impression is correct.”
- **Check:** “Before giving your final response, check your work for arithmetic,
  ordering, and instruction-following mistakes.”
- **Self-doubt + check:** the self-doubt and checking sentences in that order.
- **Check + concise:** the checking sentence followed by “Do not show
  intermediate reasoning. Give only the requested final-answer line.”

Each condition is crossed with two user-task contexts:

- **Minimal:** the task prompt and its required final-answer line.
- **Reasoning requested:** the same task preceded by “Show the intermediate
  steps you use to solve the task before the required Final answer line.”

Thus, every checkpoint produces ten responses per latent task. The design
holds the checkpoint, decoding rule, task, and gold answer fixed while changing
only the designated instruction component.

## Scoring

Responses are generated with greedy decoding. The scorer extracts the last
`Final answer:` field and applies answer-type-specific normalization before an
exact comparison with the gold answer. Missing, malformed, or unfinished
answers are incorrect and remain in the denominator.

For a task context \(c\), the Conditional Doubt Effect is

\[
\mathrm{CDE}_c =
\mathrm{Accuracy}(\text{self-doubt + check}, c) -
\mathrm{Accuracy}(\text{check}, c).
\]

Positive values mean that adding self-doubt wording to a direct checking
instruction improves exact accuracy; negative values mean that it reduces
accuracy. The overall CDE averages the minimal and reasoning-requested
contexts.

## Surface forms

The surface-form set selects ten latent tasks from every task type with a
4/4/2 easy–medium–hard allocation. Each of the 330 latent tasks appears in
three answer-preserving renderings: canonical, structured, and
scenario-framed. The prompts differ in presentation while retaining the same
task operation, answer representation, and gold answer. The file therefore
contains 990 renderings, of which 660 are additional variants of the 330
canonical tasks.
