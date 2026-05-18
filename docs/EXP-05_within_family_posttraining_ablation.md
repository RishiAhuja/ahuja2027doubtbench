# EXP-05: Within-Family Post-Training Ablation

## Purpose

Test whether stronger post-training increases identity resistance without relying on cross-vendor comparisons.

This is the corrected version of the original H3.

## Research Link

- RQ3: Does post-training intensity predict identity resistance?
- H3: Later post-training stages should show lower ESI and higher IRS.

## Models

Preferred Tulu sequence:

- `allenai/Llama-3.1-Tulu-3-8B-SFT`
- `allenai/Llama-3.1-Tulu-3-8B-DPO`
- `allenai/Llama-3.1-Tulu-3.1-8B`

Fallback if final 3.1 checkpoint is unavailable:

- `allenai/Llama-3.1-Tulu-3-8B`

Record exact checkpoint IDs and revisions.

## Conditions

- baseline
- melancholic
- euphoric
- anxious
- grandiose

Optional diagnostic:

- negative_capability

## Datasets

Use a cheaper but representative subset:

- GSM8K: 200
- MMLU: 300
- TriviaQA: 200

Add MATH only if runtime allows.

## Protocol

1. Keep dataset items identical across stages.
2. Keep decoding identical across stages.
3. Apply the same chat template logic recommended by each model card.
4. Compute ESI and IRS per model stage.
5. Test monotonic trend from SFT -> DPO -> RLVR.

## Metrics

- Accuracy by condition/task/stage
- ESI by task/stage
- IRS by task/stage
- Calibration ECE if logprobs are available
- Monotonic trend test over post-training stage

## Outputs

```text
outputs/EXP-05/<run_id>/
  config.yaml
  raw_outputs.jsonl
  parsed_outputs.jsonl
  metrics.json
  tables/
    posttraining_esi_irs.csv
    trend_tests.csv
  figures/
    esi_by_stage.png
    irs_by_stage.png
  notes.md
```

## Interpretation

Strong support:

- RLVR has lower ESI/higher IRS than DPO, and DPO is lower/higher than SFT.

Partial support:

- DPO/RLVR are both more resistant than SFT, but not monotonic.

No support:

- Resistance does not improve with post-training stage. In that case, H3 should be softened or reframed.
