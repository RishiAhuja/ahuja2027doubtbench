# Experiment Code

Experiment runbooks live in `../docs/`.

Code layout:

- `exp01/`: multi-judge prompt audit and optional prompt polishing loop

Run EXP-01:

```bash
python -m experiments.exp01.run_audit --out outputs/EXP-01/baseline_$(date +%Y%m%d_%H%M%S)
python -m experiments.exp01.run_audit --polish --max-rounds 3 --out outputs/EXP-01/polished_$(date +%Y%m%d_%H%M%S)
```
