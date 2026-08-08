# Generation-budget diagnostic

Date: 2026-08-08 (Asia/Kolkata)

This diagnostic is excluded from confirmatory PAIR-CTRL results. It records why
the open-model campaign was restarted with a larger output budget.

## Qwen run 26474

- Model: `Qwen/Qwen2.5-7B-Instruct`
- Tasks: 400 flexibility/rule-learning tasks from seed 16061
- Design: five prompt conditions by two task contexts (4,000 rows)
- Output ceiling: 384 new tokens
- Completeness: 4,000 raw and 4,000 parsed rows

The minimal context was mostly within tolerance. In the reasoning-requested
context, however, every non-concise condition failed the predeclared 2% quality
gate:

| Condition | Parse failure | Truncation |
|---|---:|---:|
| neutral | 14.25% | 18.50% |
| self-doubt | 14.75% | 19.00% |
| check | 19.50% | 24.00% |
| self-doubt + check | 12.00% | 16.25% |
| check + concise | 0.00% | 0.00% |

The failure is condition-dependent: prompts that elicit longer visible
reasoning hit the ceiling more often. Accuracy contrasts from this run would
therefore mix behavioral effects with differential missing final answers.

## Decision

- Exclude Qwen `26474` from confirmatory analysis.
- Stop the contemporaneous 384-token Llama diagnostic `26477` at 3,336/4,000
  raw rows; it did not complete and is also excluded.
- Rerun every primary and secondary campaign component with a 768-token ceiling.
- Admit a replacement run only after checking completeness, per-cell parse
  failures, and per-cell truncation against the 2% gates.

Local provenance is retained under
`outputs/PAIR-CTRL/qwen_ext16061_26474.master/` and
`outputs/PAIR-CTRL/llama_ext16061_26477.master/`.
