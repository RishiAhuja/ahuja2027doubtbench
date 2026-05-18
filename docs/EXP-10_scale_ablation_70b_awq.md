# EXP-10: Scale Ablation with 70B Quantized Model

## Purpose

Check whether observed effects persist at larger scale.

This is a stretch experiment because 70B inference is slower and quantization adds a confound.

## Research Link

- External validity for RQ1/RQ2.
- Tests whether larger models are more identity-resistant.

## Model

Use a pinned quantized checkpoint of:

- Llama 3.1 70B Instruct, AWQ/GPTQ/FP8 if available and stable on the target H100.

Record the exact quantized repository, quantization method, revision, vLLM version, and GPU memory settings.

## Conditions

Minimal subset:

- baseline
- melancholic
- anxious
- grandiose
- negative_capability

## Datasets

- GSM8K: 100
- MMLU: 150
- TriviaQA: 100

## Protocol

1. First run 10-item smoke test for each dataset.
2. Compare baseline accuracy against expected range for the quantized model.
3. If quantization degrades baseline heavily, stop and do not use results for paper claims.
4. Run full subset only after smoke test passes.

## Metrics

- Accuracy delta
- ESI
- IRS
- Negative-capability excess from EXP-02 formula

## Outputs

```text
outputs/EXP-10/<run_id>/
  config.yaml
  quantization_manifest.json
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    scale_ablation_deltas.csv
  figures/
    scale_comparison.png
  notes.md
```

## Interpretation

Use cautiously. If the effect differs from 8B models, it may be due to scale, quantization, chat template, or model family details.
