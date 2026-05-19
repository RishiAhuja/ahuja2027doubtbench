# EXP-02 Overnight Run — 2026-05-19

Cluster batch: `batch_20260519_021504`

- **GSM8K:** 100 items (test set, first 100)
- **MMLU:** 100 items (simple-evals CSV, first 100)
- **Conditions:** baseline, melancholic, negative_capability
- **Decoding:** greedy, max_new_tokens=256
- **Total:** 600 rows per model × 3 models = 1,800 rows

## Models

| Directory | Model |
|-----------|--------|
| `Qwen_Qwen2.5-7B-Instruct/` | Qwen/Qwen2.5-7B-Instruct |
| `meta-llama_Llama-3.1-8B-Instruct/` | meta-llama/Llama-3.1-8B-Instruct |
| `mistralai_Mistral-7B-Instruct-v0.3/` | mistralai/Mistral-7B-Instruct-v0.3 |

Interpretation: [docs/EXP-02_OVERNIGHT_RESULTS.md](../../docs/EXP-02_OVERNIGHT_RESULTS.md)
