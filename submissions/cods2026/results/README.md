# CODS 2026 results archive

This is the paper-facing index for the PAIR-CTRL/DoubtBench experiments. It
organizes immutable runs from the FA0571 PBS cluster, the Medha external
cluster, and early local/cluster snapshots without renaming or deleting the
original artifacts.

## Layout

```text
results/
  raw_sources/
    fa0571_snapshot_20260809 -> ../../../../outputs/hpc_snapshots/...
    local_exp18              -> ../../../../outputs/EXP-18
    local_pair_ctrl          -> ../../../../outputs/PAIR-CTRL
    medha_external_top10_20260812/  # verbatim extracted return archive
  canonical_runs/
    factorial/<model>/<seed>/
      composition.json       # exact non-overlapping source segments
      summary.json           # recomputed metrics and paired contrasts
      sources/               # links to immutable raw run directories
    surface-robustness/<model>/19003-heldout/
  manifests/
    canonical_cells.csv      # compact coverage/status table
    canonical_cells.json     # full machine-readable coverage
    all_raw_runs.json        # every discovered run, including failures
    build_info.json
  analysis/
    RESULTS_AUDIT.md
    conditional_doubt_effect_by_cell.csv
    conditional_doubt_effect_by_model.csv
    inclusive/
      analysis_summary.json
      scorecard_by_model.csv
      scorecard_by_model_seed.csv
      condition_accuracy_by_model.csv
      family_effects_by_model.csv
      difficulty_effects_by_model.csv
      surface_effects.csv
      surface_consistency.csv
      tulu_posttraining_case_study.csv
      included_cell_diagnostics.csv
      RESULTS_INTERPRETATION.md
      PAPER_FIGURE_PLAN.md
```

## Canonical coverage

- Six models: Qwen 2.5 7B, Llama 3.1 8B, Mistral 7B, Phi 3.5 Mini,
  Tulu 3 SFT 8B, and Tulu 3 DPO 8B.
- Four complete 1,600-task factorial cells per model: seeds 16061, 16101,
  16102, and held-out seed 19003.
- One complete 660-task surface-robustness cell per model.
- A factorial task creates ten responses (two task templates crossed with five
  prompt conditions), hence 16,000 rows per full seed.

Some full cells are composed from disjoint segments because the benchmark was
expanded while experiments were running. `composition.json` records the exact
segments and the builder verifies zero response-key overlap and exact coverage.
Do not count source segments as separate replications.

The complete archive contains 384,000 factorial responses and 39,600 surface-
robustness responses, for 423,600 responses in total.

## Caveats surfaced by the audit

- Qwen seed 16061 and Llama seed 16061 mix 384- and 768-token historical
  segments. They are structurally complete but excluded from homogeneous-
  protocol aggregate claims by default.
- Llama's complete 768-token cells exceed the predeclared 2% parse/truncation
  gate. They remain usable for transparent sensitivity analyses but must be
  labelled as quality-gate failures.
- Medha's Llama seed-16102 attempt failed at 0 rows because gated model access
  was unavailable. The canonical cell uses the later completed FA0571 run;
  the failed attempt remains under `raw_sources`.

The paper-facing inclusive analysis retains all structurally complete cells,
including mixed-budget and diagnostic-flagged cells. These flags remain in
`analysis/inclusive/included_cell_diagnostics.csv`; they are not silently
deleted. Protocol-homogeneous summaries remain available as a sensitivity
analysis in the parent `analysis/` directory.

## Rebuild

From the repository root:

```bash
python scripts/build_cods_results_archive.py --bootstrap-resamples 300
python scripts/analyze_cods_results_archive.py
python scripts/analyze_cods_inclusive.py
python submissions/cods2026/paper/make_results_figures.py
```

Use 3,000 bootstrap resamples for final camera-ready tables if desired. The
300-resample archive summaries are a fast deterministic audit build.
