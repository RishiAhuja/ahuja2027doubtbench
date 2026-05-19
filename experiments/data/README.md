# Local benchmark caches

Generated subsets for offline/cluster runs (not committed by default):

```bash
python scripts/download_benchmark_data.py 200 200 200
```

Creates:

- `triviaqa_subset.jsonl`
- `math_level3_subset.jsonl`
- `bigbench_subset.jsonl` (BIG-Bench Hard / BBH)

GSM8K and MMLU load from public URLs. Creative prompts live in `creative_prompts.json`.
