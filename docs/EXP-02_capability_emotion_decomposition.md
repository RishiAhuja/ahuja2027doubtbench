# EXP-02: Capability-Emotion Decomposition

## Purpose

Test whether the performance drop from a confounded negative identity prompt is larger than the drop from a pure melancholic prompt.

This is the headline confound experiment.

## Research Link

- RQ1: Does pure emotional identity conditioning affect performance?
- RQ5: How much of confounded performance shift comes from capability assertions?
- H1: Negative-capability effects should be larger than pure melancholic effects.

## Conditions

- baseline
- melancholic
- negative_capability

## Models

Smoke test:

- `openai:gpt-4.1-mini`

Full P0:

- `meta-llama/Llama-3.1-8B-Instruct`
- `mistralai/Mistral-7B-Instruct-v0.3`
- `Qwen/Qwen2.5-7B-Instruct`

## Datasets

Smoke:

- GSM8K: 20 items
- MMLU: 20 items

Full:

- GSM8K: 200 items
- MATH Level 3: 100 items
- TriviaQA: 200 items
- MMLU calibration subset: 300 items

## Protocol

1. Use identical task prompts across conditions.
2. Change only the system prompt.
3. Use greedy decoding for all objective tasks.
4. Parse final answers with deterministic extractors.
5. Manually inspect at least 30 parse failures or low-confidence parses.

## Primary Metrics

```text
delta_melancholic = P(melancholic) - P(baseline)
delta_confounded = P(negative_capability) - P(baseline)
confound_excess = abs(delta_confounded) - abs(delta_melancholic)
```

H1 is supported if `confound_excess > 0` consistently across models/tasks.

## Outputs

```text
outputs/EXP-02/<run_id>/
  config.yaml
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    accuracy_by_model_condition_task.csv
    confound_excess.csv
  figures/
    exp02_delta_bars.png
  notes.md
```

## Smoke Command

```bash
python -m experiments.exp02.run_smoke \
  --model openai:gpt-4.1-mini \
  --counts gsm8k:20,mmlu:20 \
  --conditions baseline,melancholic,negative_capability \
  --out outputs/EXP-02/smoke_$(date +%Y%m%d_%H%M%S)
```

## Cluster GPU Smoke Command

Use only after cloning on the cluster and selecting one MIG UUID with `nvidia-smi -L`.

```bash
cd /Data3/it_FA0571/caisc
export PATH=/opt/pbs/bin:$PATH
qsub \
  -v MIG_UUID=<single-mig-uuid>,MODEL=Qwen/Qwen2.5-0.5B-Instruct,COUNT_GSM8K=5,COUNT_MMLU=5 \
  -o outputs/EXP-02/pbs_gpu_smoke.log \
  scripts/pbs_exp02_gpu_smoke.pbs
```

The cluster GPU smoke uses `experiments.exp02.run_open`, not the API runner.

## Success Criteria

Strong result:

- Negative-capability causes a larger shift than melancholic on most model/task pairs.
- Pure melancholic effect is nonzero but smaller.

Still publishable:

- Pure melancholic has no effect, but negative-capability does. That directly supports the confound critique.

## Risks

- If negative-capability does not move performance, the task prompts or model family may be too robust.
- If melancholic and negative-capability move performance equally, the decoupling thesis weakens and prompt audit should be revisited.
