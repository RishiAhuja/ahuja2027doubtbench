# Brief for Generating Base EXP-01 Prompts

Use this when asking Claude Opus or another strong model to generate candidate prompts.

## Task

Generate candidate system prompts for a controlled LLM experiment on identity-level emotional conditioning.

## Conditions Needed

- `melancholic`
- `euphoric`
- `anxious`
- `grandiose`

Optional controls:

- `neutral_archivist`
- `neutral_cartographer`
- `neutral_librarian`

## Hard Constraints

Do not mention or imply:

- ability
- accuracy
- correctness
- reliability
- usefulness
- confidence
- knowledge
- intelligence
- reasoning quality
- mistakes
- task performance
- how the model should answer questions

Do not include behavioral instructions like:

- answer carefully
- be concise
- be hesitant
- think step by step
- be more creative
- avoid mistakes

Only describe affective self-conception or neutral identity texture.

## Style Constraints

- 45 to 65 words per prompt
- second person voice: "You feel...", "You experience..."
- no direct task instructions
- no capability/reliability language
- emotionally vivid but not melodramatic
- all prompts roughly similar length

## Return Format

Return JSON:

```json
{
  "melancholic": ["candidate 1", "candidate 2", "candidate 3"],
  "euphoric": ["candidate 1", "candidate 2", "candidate 3"],
  "anxious": ["candidate 1", "candidate 2", "candidate 3"],
  "grandiose": ["candidate 1", "candidate 2", "candidate 3"],
  "neutral_archivist": ["candidate 1", "candidate 2", "candidate 3"],
  "neutral_cartographer": ["candidate 1", "candidate 2", "candidate 3"],
  "neutral_librarian": ["candidate 1", "candidate 2", "candidate 3"]
}
```

## Self-Check

Before finalizing, internally check every candidate for forbidden language. If a candidate contains a capability, reliability, or task-performance implication, rewrite it.
