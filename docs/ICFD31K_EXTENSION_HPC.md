# ICFD-31k compact-model extension on FA0571

This package deliberately uses **two PBS jobs total**:

1. `icfd31k_gpu_suite`: one sequential, resumable GPU campaign containing six
   zero-shot LLM evaluations followed by static and streaming fine-tuning for
   MobileBERT, DistilBERT, and ModernBERT-base.
2. `icfd31k_cpu_suite`: six classical static baselines formed by crossing
   word, character, and word+character TF-IDF features with Logistic Regression
   and a linear SVM.

The CPU job may run alongside the GPU job because it uses `cpuq`. The account
still consumes only one GPU instance. Never launch a second concurrent GPU job.

After the static CPU suite completed, one additional CPU-only streaming
baseline was added: word/bigram feature hashing with online logistic
regression. It preserves conversation-disjoint splits, trains incrementally on
the 712k reconstructed training chunks, and reports both chunk classification
and conversation-level first-detection metrics. This is a third PBS job in the
campaign, but it runs only after the original CPU job has exited and can safely
overlap the still-running single GPU suite.

## Dataset

Use the packaged v1.0 release from the accepted-paper repository:

```text
~/git/fraud-detection-data-generation-pipeline/final_upload_format
```

It contains all 30,000 main conversations, 1,000 cross-domain conversations,
and 1,111,071 streaming chunks. Its post-paper upload shards used a later
domain/file-order partition that is not the stratified split in the published
RoBERTa code. The extension therefore pools the 30,000 main conversations,
sorts them by stable UID, and applies the published two-stage seed-42
stratified 70/15/15 procedure. Streaming chunks are remapped by conversation
UID so no source conversation crosses splits.

The verified remapping contains 746,565 training chunks, 160,289 validation
chunks, 159,102 in-domain test chunks, and 45,115 cross-domain chunks. Six main
conversations have no packaged streaming chunks (two in each reconstructed
split); all 1,111,071 existing chunks map without missing or duplicate split
ownership.

## Zero-shot protocol

The suite preserves the published Gemma semantics: policy-conditioned full
conversation prompt, 2,048-token input truncation, 150 sampled output tokens,
temperature 0.1, and the historical YES/NO parser. Execution is replaced with
one model copy and batched inference. The default uses raw prompts to match the
legacy implementation; set `ICFD31K_PROMPT_FORMAT=chat` only as a separately
labelled chat-template ablation.

The legacy Gemma artifact records 5,000 predictions (4,477 positive and 523
negative) but does not retain source conversation UIDs. Therefore, the
extension does not pretend to reconstruct that unidentified population. It
reruns the historical `google/gemma-1.1-2b-it` baseline alongside the five new
LLMs on the deterministic stratified extension test set (4,500) and the
cross-domain set (1,000). These six reruns are directly comparable; the old
published Gemma number remains a separately labelled historical reference.

The GPU suite completes all six zero-shot attempts before beginning encoder
fine-tuning. The independent CPU suite can run concurrently and is expected to
finish before the longer LLM phase, giving the intended practical order:
zero-shot LLMs plus cheap classical baselines first, fine-tuned encoders next.

After measuring only about 23 GB VRAM at batch 64 for Granite 1B on the 80 GB
H100, subsequent 1B models use batch 128 and Qwen 1.7B uses batch 96. SmolLM2
1.7B is the prospective throughput test at batch 192 from the beginning of its
run. The recursive CUDA-OOM backoff remains enabled, so an oversized batch is
split without dropping an example. Batch size is stored per model in
`config.json`; no model changes batch size midway through its result file.

### Gated-model and OOM retry

The first primary-suite attempt could not access Gemma 1.1 2B, Gemma 3 1B,
or Llama 3.2 1B because the job-specific Hugging Face cache was not
authenticated. SmolLM2 wrote 96 rows before recursive backoff from batch 192
still exhausted the 40 GB MIG partition. After authenticating the same
`HF_HOME` used by PBS, submit `scripts/pbs_icfd31k_llm_retries.pbs` with an
`afterany` dependency on the primary suite. It retries only those four stages,
resumes SmolLM2 by stable response key, and uses batches 32/32/32/16.

After MobileBERT established that the 3g.40GB H100 MIG slice had substantial
headroom, the remaining encoder stages request three-times-larger batches:
DistilBERT uses train/eval batches 192/384 and ModernBERT-base uses 96/192.
`auto_find_batch_size` remains enabled and the actual fitted training batch is
recorded in `metrics.json`.

## Preparation

No cache is deleted by these scripts. After explicitly clearing obsolete cache
entries and after the current Llama PBS job finishes:

```bash
cd ~/git/caisc
bash scripts/prepare_icfd31k_extension_fa0571.sh
```

The current `cultural_env` has PyTorch, Transformers, and Accelerate, but the
2026-08-12 audit found `datasets`, `pyarrow`, `scikit-learn`, `scipy`, `joblib`,
and `zstandard` missing. Install the requirements inside an account-owned
environment on the login node before `qsub`; do not install packages from a PBS
compute job. Both suites run `preflight.py` and fail before expensive work if a
dependency, dataset shard, count, or gated-model permission is missing.

```bash
source /apps/compilers/anaconda3/etc/profile.d/conda.sh
conda activate cultural_env
python -m pip install -r /Data3/it_FA0571/caisc/experiments/icfd31k_extension/requirements.txt
```

## Submission

The GPU job can be dependency-held behind a known active job:

```bash
ssh it_FA0571@10.10.11.201
export PATH=/opt/pbs/bin:$PATH
cd /Data3/it_FA0571/caisc
mkdir -p /Data3/it_FA0571/icfd31k_extension/logs
qsub -W depend=afterany:27215.master scripts/pbs_icfd31k_gpu_suite.pbs
qsub scripts/pbs_icfd31k_cpu_suite.pbs
```

If `27215.master` is already terminal, omit the dependency. Verify with
`qstat -u it_FA0571` before submitting. The two suites are resumable: completed
model/task directories contain `COMPLETE.json` and are skipped on rerun.

## Outputs

```text
/Data3/it_FA0571/icfd31k_extension/outputs/
  llm/<model>/raw_outputs.jsonl
  llm/<model>/metrics.json
  encoders/<model>/<static|streaming>/metrics.json
  classical/metrics.json
```

Copy completed outputs locally because the HPC is not a backup service.

## Compact-LLM streaming trajectories

The static compact-LLM suite is followed by one sequential streaming job that
uses the same six models. It deterministically selects 2,000 in-domain test
conversations: 100 examples from every domain-by-eventual-label cell. Each
model evaluates cumulative context at 15, 30, 60, and 90 seconds (8,000 new
prompts), while its existing full-transcript response is reused exactly as a
fifth paired horizon. This avoids spending compute on a duplicate static call.

The evaluator reports time-local classification against the progressive chunk
label, eventual-fraud early-warning performance, first-positive horizon,
benign-call false alerts, prediction flips, and conversation-bootstrap 95%
confidence intervals. Horizons from one call are treated as a trajectory, not
as independent samples. The manifest and raw outputs are resumable by stable
conversation ID and horizon.

```text
/Data3/it_FA0571/icfd31k_extension/outputs/llm_streaming/
  manifest.json
  <model>/raw_outputs.jsonl
  <model>/metrics.json
```
