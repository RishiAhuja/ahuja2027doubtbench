#!/usr/bin/env python3
"""Build the compact, anonymous DoubtBench WSDM artifact.

The released package uses public module names only. Lab experiment IDs
(exp02/exp14/exp16/exp18), the pair_ctrl codename, and unrelated emotion /
GSM8K scaffolding are not shipped.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import textwrap
import zipfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "submissions" / "wsdm2027" / "DoubtBench_WSDM_Artifact"
ZIP_OUT = ROOT / "submissions" / "wsdm2027" / "DoubtBench_WSDM_Code_Data_Artifact.zip"

TASK_SOURCES = {
    "task_set_16061": ROOT / "benchmarks/pair_ctrl/eval_batches/seed16061_full.jsonl",
    "task_set_16101": ROOT / "benchmarks/pair_ctrl/eval_batches/seed16101_full.jsonl",
    "task_set_16102": ROOT / "benchmarks/pair_ctrl/eval_batches/seed16102_full.jsonl",
    "task_set_19003": ROOT / "benchmarks/pair_ctrl/eval_batches/heldout_19003_full.jsonl",
}
SURFACE_SOURCE = (
    ROOT / "benchmarks/pair_ctrl/data/pair_ctrl_heldout_19003_surface_robustness.jsonl"
)
RESULT_SOURCE = ROOT / "submissions/cods2026/results/analysis/inclusive"
FIGURE_SOURCE = ROOT / "submissions/cods2026/paper/figures/results"


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(rows: list[dict]) -> dict[str, dict[str, int]]:
    return {
        field: dict(sorted(Counter(str(row[field]) for row in rows).items()))
        for field in ("family", "task_type", "difficulty", "answer_type")
    }


def clean_metadata(metadata: dict, task_set: str) -> dict:
    cleaned = {key: value for key, value in metadata.items() if key != "pair_ctrl"}
    cleaned["doubtbench"] = {"task_set": task_set}
    return cleaned


def clean_task_set(task_set: str, source: Path) -> tuple[list[dict], dict[str, str]]:
    rows = read_jsonl(source)
    cleaned: list[dict] = []
    original_to_public: dict[str, str] = {}
    legacy_to_public: dict[str, str] = {}
    for index, row in enumerate(rows, start=1):
        new_id = f"doubtbench_{task_set}_{index:04d}"
        original_to_public[str(row["task_id"])] = new_id
        pair_meta = (row.get("metadata") or {}).get("pair_ctrl") or {}
        legacy_id = pair_meta.get("legacy_task_id")
        if legacy_id:
            legacy_to_public[str(legacy_id)] = new_id
        clean = dict(row)
        clean["task_id"] = new_id
        clean["dataset"] = "doubtbench"
        clean["metadata"] = clean_metadata(dict(row.get("metadata") or {}), task_set)
        cleaned.append(clean)
    return cleaned, {**original_to_public, **legacy_to_public}


def write_task_set(task_set: str, rows: list[dict]) -> None:
    path = OUT / "data" / f"{task_set}.jsonl"
    write_jsonl(path, rows)
    manifest = {
        "benchmark": "DoubtBench",
        "task_set": task_set,
        "generation_seed": int(task_set.rsplit("_", 1)[1]),
        "task_count": len(rows),
        "expected_factorial_responses_per_checkpoint": len(rows) * 10,
        "sha256": sha256(path),
        "counts": inventory(rows),
    }
    path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def clean_surface_rows(public_id_map: dict[str, str], canonical_rows: list[dict]) -> list[dict]:
    canonical_by_public = {row["task_id"]: row for row in canonical_rows}
    source_rows = read_jsonl(SURFACE_SOURCE)
    grouped: dict[str, dict[str, dict]] = {}
    for row in source_rows:
        pair_meta = row["metadata"]["pair_ctrl"]
        legacy_id = str(pair_meta["legacy_task_id"])
        public_main_id = public_id_map.get(legacy_id)
        if public_main_id is None:
            raise RuntimeError(f"No canonical task for surface item {legacy_id}")
        grouped.setdefault(public_main_id, {})[str(pair_meta["surface_variant"])] = row

    output: list[dict] = []
    for latent_index, public_main_id in enumerate(sorted(grouped), start=1):
        variants = grouped[public_main_id]
        if set(variants) != {"structured", "scenario"}:
            raise RuntimeError(f"Incomplete surface forms for {public_main_id}: {sorted(variants)}")
        latent_id = f"doubtbench_surface_latent_{latent_index:04d}"
        source_forms = {"canonical": canonical_by_public[public_main_id], **variants}
        for surface_form in ("canonical", "structured", "scenario"):
            row = dict(source_forms[surface_form])
            row["task_id"] = f"{latent_id}_{surface_form}"
            row["dataset"] = "doubtbench"
            metadata = {
                key: value
                for key, value in dict(row.get("metadata") or {}).items()
                if key != "pair_ctrl"
            }
            metadata["doubtbench"] = {
                "task_set": "surface_forms",
                "latent_task_id": latent_id,
                "main_task_id": public_main_id,
                "surface_form": surface_form,
            }
            row["metadata"] = metadata
            output.append(row)
    return output


def write_surface(rows: list[dict]) -> None:
    path = OUT / "data" / "surface_forms.jsonl"
    write_jsonl(path, rows)
    latent_ids = {row["metadata"]["doubtbench"]["latent_task_id"] for row in rows}
    forms = Counter(row["metadata"]["doubtbench"]["surface_form"] for row in rows)
    manifest = {
        "benchmark": "DoubtBench",
        "task_set": "surface_forms",
        "latent_task_count": len(latent_ids),
        "rendering_count": len(rows),
        "additional_answer_preserving_variants": len(rows) - len(latent_ids),
        "surface_form_counts": dict(sorted(forms.items())),
        "sha256": sha256(path),
        "counts": inventory(rows),
    }
    path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        if old not in text:
            raise RuntimeError(f"Expected text not found during scrubbing:\n{old[:120]}")
        text = text.replace(old, new)
    return text


def emit_core() -> None:
    (OUT / "core").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "core/json_utils.py", OUT / "core/json_utils.py")
    write_text(
        OUT / "core/__init__.py",
        '''
        """Shared helpers for the DoubtBench artifact."""
        ''',
    )


def emit_evaluation() -> None:
    evaluation = OUT / "evaluation"
    evaluation.mkdir(parents=True, exist_ok=True)
    write_text(
        evaluation / "__init__.py",
        '''
        """DoubtBench evaluation helpers and factorial runner."""
        ''',
    )
    write_text(
        evaluation / "io_utils.py",
        '''
        """Small CSV and JSONL helpers for evaluation outputs."""

        from __future__ import annotations

        import csv
        import json
        from pathlib import Path
        from typing import Any


        def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
            if not rows:
                return
            fieldnames = list(rows[0].keys())
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)


        def append_jsonl(path: Path, row: dict[str, Any]) -> None:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\\n")
        ''',
    )
    write_text(
        evaluation / "hf_model.py",
        '''
        """Load open Hugging Face causal language models for DoubtBench."""

        from __future__ import annotations

        import os


        def load_hf_model(model_name: str, cache_dir: str | None):
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            # Prefer Transformers' native Phi-3 implementation over remote repo code.
            default_trust_remote_code = not model_name.lower().startswith("microsoft/phi-3")
            override = os.getenv("HF_TRUST_REMOTE_CODE")
            trust_remote_code = (
                default_trust_remote_code
                if override is None
                else override.strip().lower() in {"1", "true", "yes", "on"}
            )
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                trust_remote_code=trust_remote_code,
            )
            if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
                tokenizer.pad_token = tokenizer.eos_token
            tokenizer.padding_side = "left"

            kwargs = {
                "cache_dir": cache_dir,
                "trust_remote_code": trust_remote_code,
                "device_map": "auto",
            }
            if torch.cuda.is_available():
                kwargs["torch_dtype"] = torch.bfloat16
            model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
            model.eval()
            return tokenizer, model
        ''',
    )

    shutil.copy2(ROOT / "experiments/exp14/trace.py", evaluation / "trace.py")
    write_text(
        evaluation / "generation.py",
        '''
        """Greedy generation helpers for open Hugging Face models."""

        from __future__ import annotations

        from typing import Any


        THINKING_MODES = {"auto", "on", "off"}


        def render_chat(tokenizer, system_prompt: str, user_prompt: str, thinking_mode: str) -> str:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
                kwargs = {
                    "tokenize": False,
                    "add_generation_prompt": True,
                }
                if thinking_mode != "auto":
                    kwargs["enable_thinking"] = thinking_mode == "on"
                try:
                    return tokenizer.apply_chat_template(messages, **kwargs)
                except TypeError as exc:
                    if thinking_mode != "auto":
                        raise RuntimeError(
                            f"Tokenizer chat template does not support thinking_mode={thinking_mode!r}"
                        ) from exc
                    raise
            return f"System:\\n{system_prompt}\\n\\nUser:\\n{user_prompt}\\n\\nAssistant:\\n"


        def normalize_token_ids(token_ids: Any) -> set[int]:
            if token_ids is None:
                return set()
            if isinstance(token_ids, int):
                return {token_ids}
            return {int(token_id) for token_id in token_ids}


        def trim_generated_ids(token_ids: list[int], terminal_ids: set[int]) -> tuple[list[int], bool]:
            for index, token_id in enumerate(token_ids):
                if token_id in terminal_ids:
                    return token_ids[: index + 1], True
            return token_ids, False


        def generate_batch(tokenizer, model, prompts: list[str], max_new_tokens: int) -> list[dict[str, Any]]:
            import torch

            encoded = tokenizer(prompts, return_tensors="pt", padding=True)
            encoded = {key: value.to(model.device) for key, value in encoded.items()}
            terminal_ids = normalize_token_ids(
                getattr(model.generation_config, "eos_token_id", None) or tokenizer.eos_token_id
            )
            with torch.inference_mode():
                output_ids = model.generate(
                    **encoded,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=getattr(model.generation_config, "eos_token_id", None)
                    or tokenizer.eos_token_id,
                )

            prompt_width = encoded["input_ids"].shape[-1]
            rows = []
            for output in output_ids[:, prompt_width:]:
                generated_ids = [int(token_id) for token_id in output.tolist()]
                trimmed_ids, ended_on_terminal = trim_generated_ids(generated_ids, terminal_ids)
                rows.append(
                    {
                        "raw_output": tokenizer.decode(trimmed_ids, skip_special_tokens=False).strip(),
                        "generated_token_count": len(trimmed_ids),
                        "ended_on_terminal": ended_on_terminal,
                        "truncated": len(generated_ids) >= max_new_tokens and not ended_on_terminal,
                    }
                )
            return rows


        def text_token_count(tokenizer, text: str) -> int | None:
            if not text:
                return 0
            try:
                encoded = tokenizer(text, add_special_tokens=False)
                return len(encoded["input_ids"])
            except Exception:  # noqa: BLE001
                return None


        def model_metadata(model, tokenizer) -> dict[str, Any]:
            import torch
            import transformers

            return {
                "torch_version": torch.__version__,
                "transformers_version": transformers.__version__,
                "model_config_commit_hash": getattr(model.config, "_commit_hash", None),
                "tokenizer_commit_hash": getattr(tokenizer, "_commit_hash", None)
                or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash"),
                "chat_template_present": bool(getattr(tokenizer, "chat_template", None)),
                "eos_token_id": getattr(tokenizer, "eos_token_id", None),
                "pad_token_id": getattr(tokenizer, "pad_token_id", None),
            }


        def has_explicit_final_answer(text: str) -> bool:
            return "final answer" in text.lower()
        ''',
    )
    write_text(
        evaluation / "tasks.py",
        '''
        """Load DoubtBench JSONL tasks and score generated answers."""

        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Any

        from doubtbench.scoring import extract_final_answer, score_task_row_output


        def load_tasks(path: Path) -> list[dict[str, Any]]:
            rows = []
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        rows.append(json.loads(line))
            if not rows:
                raise SystemExit(f"No DoubtBench tasks found in {path}")
            return rows


        def score_generation(task: dict[str, Any], text: str) -> tuple[str, bool, str | None]:
            try:
                parsed = extract_final_answer(text)
                score = score_task_row_output(task, text)
                return parsed, score, None
            except Exception as exc:  # noqa: BLE001
                return "", False, f"{type(exc).__name__}: {exc}"
        ''',
    )

    factorial_src = (ROOT / "experiments/exp18/run_open_factorial.py").read_text(encoding="utf-8")
    factorial = apply_replacements(
        factorial_src,
        [
            (
                '"""Run the EXP-18 common-prefix factorial on open Hugging Face models.',
                '"""Run the DoubtBench common-prefix factorial on open Hugging Face models.',
            ),
            (
                "from core.env import load_dotenv\n"
                "from core.json_utils import write_json, write_jsonl\n"
                "from experiments.exp02.common import append_jsonl, write_csv\n"
                "from experiments.exp02.run_open import load_hf_model\n"
                "from experiments.exp14.run_open_reasoning import (\n"
                "    THINKING_MODES,\n"
                "    generate_batch,\n"
                "    has_explicit_final_answer,\n"
                "    model_metadata,\n"
                "    render_chat,\n"
                "    text_token_count,\n"
                ")\n"
                "from experiments.exp14.trace import extract_visible_reasoning\n"
                "from experiments.exp16.run_open_cognitive import load_tasks, score_generation\n",
                "from core.json_utils import write_json, write_jsonl\n"
                "from evaluation.generation import (\n"
                "    THINKING_MODES,\n"
                "    generate_batch,\n"
                "    has_explicit_final_answer,\n"
                "    model_metadata,\n"
                "    render_chat,\n"
                "    text_token_count,\n"
                ")\n"
                "from evaluation.hf_model import load_hf_model\n"
                "from evaluation.io_utils import append_jsonl, write_csv\n"
                "from evaluation.tasks import load_tasks, score_generation\n"
                "from evaluation.trace import extract_visible_reasoning\n",
            ),
            ("    load_dotenv()\n    parser = argparse.ArgumentParser()\n", "    parser = argparse.ArgumentParser()\n"),
            ('EXPERIMENT_ID = "EXP-18"', 'EXPERIMENT_ID = "DoubtBench"'),
            (
                'DEFAULT_DATA_FILE = "experiments/data/exp16_self_doubt_focus_pilot.jsonl"',
                'DEFAULT_DATA_FILE = "data/task_set_16061.jsonl"',
            ),
            ("Unknown EXP-18 conditions", "Unknown DoubtBench conditions"),
            ("Unknown EXP-18 task templates", "Unknown DoubtBench task templates"),
        ],
    )
    (evaluation / "factorial.py").write_text(factorial, encoding="utf-8")


def emit_doubtbench_package() -> None:
    package = OUT / "doubtbench"
    package.mkdir(parents=True, exist_ok=True)
    write_text(
        package / "__init__.py",
        '''
        """DoubtBench task generation and exact-answer scoring."""
        ''',
    )

    scoring = (ROOT / "experiments/exp16/scoring.py").read_text(encoding="utf-8")
    scoring = apply_replacements(
        scoring,
        [
            (
                '"""Scoring helpers for EXP-16 cognitive battery tasks."""',
                '"""Exact-answer scoring helpers for DoubtBench tasks."""',
            ),
            (
                'raise ValueError(f"Unsupported EXP-16 answer_type: {answer_type}")',
                'raise ValueError(f"Unsupported DoubtBench answer_type: {answer_type}")',
            ),
        ],
    )
    (package / "scoring.py").write_text(scoring, encoding="utf-8")

    generate_tasks = (ROOT / "experiments/exp16/generate_tasks.py").read_text(encoding="utf-8")
    generate_tasks = apply_replacements(
        generate_tasks,
        [
            (
                '"""Generate EXP-16 psych-grounded cognitive battery JSONL files."""',
                '"""Core DoubtBench task generators and allocation helpers."""',
            ),
            (
                "REPO_ROOT = Path(__file__).resolve().parents[2]\n"
                'DATA_DIR = REPO_ROOT / "experiments" / "data"\n'
                "DEFAULT_SEED = 16001\n\n\n",
                "",
            ),
            (
                'return f"exp16_{family}_{task_type}_{difficulty}_{index:04d}"',
                'return f"{family}_{task_type}_{difficulty}_{index:04d}"',
            ),
            ('dataset="exp16_cognitive"', 'dataset="doubtbench"'),
        ],
    )
    generate_tasks = re.sub(
        r"\ndef generate_smoke\(seed: int, per_task_type: int\) -> list\[CognitiveTask\]:.*?(?=\n\ndef write_jsonl\()",
        "\n",
        generate_tasks,
        count=1,
        flags=re.DOTALL,
    )
    generate_tasks = re.sub(
        r"\ndef main\(\) -> int:.*?(?=\nif __name__ == \"__main__\":)",
        '''
def main() -> int:
    raise SystemExit(
        "Use generate_task_set.py to build DoubtBench task sets from these generators."
    )


''',
        generate_tasks,
        count=1,
        flags=re.DOTALL,
    )
    (package / "generate_tasks.py").write_text(generate_tasks, encoding="utf-8")

    task_generators = (ROOT / "benchmarks/pair_ctrl/task_generators_v1.py").read_text(encoding="utf-8")
    task_generators = apply_replacements(
        task_generators,
        [
            (
                '"""Additional PAIR-CTRL task families not present in the EXP-16 predecessor."""',
                '"""Additional DoubtBench task families beyond the core generator set."""',
            ),
            (
                "from experiments.exp16.generate_tasks import CognitiveTask, LETTERS, make_task",
                "from doubtbench.generate_tasks import CognitiveTask, LETTERS, make_task",
            ),
            (
                "PAIR_CTRL_ADDITIONAL_GENERATORS",
                "DOUBTBENCH_ADDITIONAL_GENERATORS",
            ),
        ],
    )
    (package / "task_generators.py").write_text(task_generators, encoding="utf-8")

    generate_split = (ROOT / "benchmarks/pair_ctrl/generate_split.py").read_text(encoding="utf-8")
    generate_split = apply_replacements(
        generate_split,
        [
            (
                '"""Generate versioned PAIR-CTRL task splits from the EXP-16 task generators.\n\n'
                "Unlike the historical EXP-16 generator, this wrapper gives every task a globally\n"
                "unique split-qualified ID and derives a separate deterministic RNG stream for\n"
                "each family.  Adding or reordering a family therefore cannot silently change the\n"
                "instances generated for another family.\n"
                '"""',
                '"""Generate deterministic DoubtBench task sets.\n\n'
                "Every task receives a globally unique task-set-qualified ID. A separate random\n"
                "stream is derived for each family, so adding or reordering one family does not\n"
                "change the instances generated for another family.\n"
                '"""',
            ),
            (
                "from experiments.exp16.generate_tasks import (\n"
                "    TASK_GENERATORS as LEGACY_TASK_GENERATORS,\n"
                "    allocate,\n"
                "    difficulty_for_index,\n"
                ")\n"
                "from experiments.exp16.scoring import score_output\n\n"
                "from benchmarks.pair_ctrl.task_generators_v1 import PAIR_CTRL_ADDITIONAL_GENERATORS\n\n\n"
                'BENCHMARK = "PAIR-CTRL"\n'
                'SCHEMA_VERSION = "1.0-candidate"\n'
                "TASK_GENERATORS = {**LEGACY_TASK_GENERATORS, **PAIR_CTRL_ADDITIONAL_GENERATORS}\n",
                "from doubtbench.generate_tasks import (\n"
                "    TASK_GENERATORS as CORE_TASK_GENERATORS,\n"
                "    allocate,\n"
                "    difficulty_for_index,\n"
                ")\n"
                "from doubtbench.scoring import score_output\n"
                "from doubtbench.task_generators import DOUBTBENCH_ADDITIONAL_GENERATORS\n\n\n"
                'BENCHMARK = "DoubtBench"\n'
                "TASK_GENERATORS = {**CORE_TASK_GENERATORS, **DOUBTBENCH_ADDITIONAL_GENERATORS}\n",
            ),
            (
                "legacy_id = task.task_id\n"
                "            metadata = dict(task.metadata)\n"
                '            metadata["pair_ctrl"] = {\n'
                '                "benchmark": BENCHMARK,\n'
                '                "schema_version": SCHEMA_VERSION,\n'
                '                "split_id": split_id,\n'
                '                "base_seed": seed,\n'
                '                "family_seed": family_rng_seed,\n'
                '                "legacy_task_id": legacy_id,\n'
                "            }\n"
                "            qualified = replace(\n"
                "                task,\n"
                '                task_id=f"pairctrl_{split_id}_{legacy_id.removeprefix(\'exp16_\')}",\n'
                '                dataset="pair_ctrl",\n'
                "                metadata=metadata,\n"
                "            )",
                "generator_id = task.task_id\n"
                "            metadata = dict(task.metadata)\n"
                '            metadata["doubtbench"] = {\n'
                '                "benchmark": BENCHMARK,\n'
                '                "task_set": split_id,\n'
                '                "generation_seed": seed,\n'
                '                "family_seed": family_rng_seed,\n'
                "            }\n"
                "            qualified = replace(\n"
                "                task,\n"
                '                task_id=f"doubtbench_{split_id}_{generator_id}",\n'
                '                dataset="doubtbench",\n'
                "                metadata=metadata,\n"
                "            )",
            ),
            ('if row["dataset"] != "pair_ctrl":', 'if row["dataset"] != "doubtbench":'),
            (
                "manifest = {\n"
                '        "benchmark": BENCHMARK,\n'
                '        "schema_version": SCHEMA_VERSION,\n'
                '        "status": "candidate_not_frozen",\n'
                '        "split_id": args.split_id,\n'
                '        "base_seed": args.seed,\n'
                "        \"family_seeds\": {family: derived_seed(args.seed, family) for family in args.families},\n"
                '        "families": args.families,\n'
                '        "per_family": args.per_family,\n'
                '        "task_count": len(rows),\n'
                '        "counts": counts,\n'
                '        "data_file": str(args.out),\n'
                '        "data_sha256": file_sha256(args.out),\n'
                '        "generator": "benchmarks/pair_ctrl/generate_split.py",\n'
                '        "source_generators": "experiments/exp16/generate_tasks.py",\n'
                "    }",
                "manifest = {\n"
                '        "benchmark": BENCHMARK,\n'
                '        "task_set": args.split_id,\n'
                '        "generation_seed": args.seed,\n'
                "        \"family_seeds\": {family: derived_seed(args.seed, family) for family in args.families},\n"
                '        "families": args.families,\n'
                '        "per_family": args.per_family,\n'
                '        "task_count": len(rows),\n'
                '        "counts": counts,\n'
                '        "data_file": str(args.out),\n'
                '        "data_sha256": file_sha256(args.out),\n'
                "    }",
            ),
        ],
    )
    (package / "generate_split.py").write_text(generate_split, encoding="utf-8")

    surface = (ROOT / "benchmarks/pair_ctrl/generate_surface_variants.py").read_text(encoding="utf-8")
    surface = apply_replacements(
        surface,
        [
            (
                'return hashlib.sha256(f"PAIR-CTRL:surface:{task_id}".encode()).hexdigest()',
                'return hashlib.sha256(f"DoubtBench:surface:{task_id}".encode()).hexdigest()',
            ),
            (
                'parser.add_argument("--split-id", default="heldout_19003_surface_robustness")',
                'parser.add_argument("--split-id", default="surface_forms")',
            ),
            (
                "from experiments.exp16.scoring import score_output",
                "from doubtbench.scoring import score_output",
            ),
            (
                'row["task_id"] = f"pairctrl_{args.split_id}_{variant}_{source_task_id}"',
                'row["task_id"] = f"doubtbench_{args.split_id}_{variant}_{source_task_id}"',
            ),
            (
                "pair_ctrl = dict(metadata.get(\"pair_ctrl\") or {})\n"
                "            metadata[\"pair_ctrl\"] = {\n"
                "                **pair_ctrl,\n"
                '                "benchmark": "PAIR-CTRL",\n'
                '                "schema_version": "1.0-candidate",\n'
                '                "split_id": args.split_id,\n'
                '                "base_seed": 19003,\n'
                '                "source_split_id": pair_ctrl.get("split_id"),\n'
                '                "source_task_id": source_task_id,\n'
                '                "surface_variant": variant,\n'
                '                "paired_latent_task_id": source_task_id,\n'
                "            }",
                "doubtbench = dict(metadata.get(\"doubtbench\") or {})\n"
                "            metadata[\"doubtbench\"] = {\n"
                "                **doubtbench,\n"
                '                "benchmark": "DoubtBench",\n'
                '                "task_set": args.split_id,\n'
                '                "generation_seed": generation_seed,\n'
                '                "source_task_set": doubtbench.get("task_set"),\n'
                '                "source_task_id": source_task_id,\n'
                '                "surface_variant": variant,\n'
                '                "latent_task_id": source_task_id,\n'
                "            }",
            ),
            (
                'sorted(Counter(row["metadata"]["pair_ctrl"]["surface_variant"] for row in rows).items())',
                'sorted(Counter(row["metadata"]["doubtbench"]["surface_variant"] for row in rows).items())',
            ),
            (
                "manifest = {\n"
                '        "benchmark": "PAIR-CTRL",\n'
                '        "schema_version": "1.0-candidate",\n'
                '        "status": "heldout_surface_robustness_not_for_prompt_development",\n'
                '        "split_id": args.split_id,\n'
                '        "base_seed": 19003,\n',
                "manifest = {\n"
                '        "benchmark": "DoubtBench",\n'
                '        "task_set": args.split_id,\n'
                '        "generation_seed": generation_seed,\n',
            ),
        ],
    )
    # Ensure generation_seed is defined if the source used a hard-coded seed.
    if "generation_seed =" not in surface:
        surface = surface.replace(
            "rows: list[dict[str, Any]] = []\n",
            "generation_seed = 19003\n    rows: list[dict[str, Any]] = []\n",
        )
    (package / "generate_surface_variants.py").write_text(surface, encoding="utf-8")


def emit_wrappers_and_scripts() -> None:
    write_text(
        OUT / "run_factorial.py",
        '''
        #!/usr/bin/env python3
        """Entry point for the DoubtBench factorial evaluator."""

        from evaluation.factorial import main


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    write_text(
        OUT / "generate_task_set.py",
        '''
        #!/usr/bin/env python3
        """Entry point for deterministic DoubtBench task-set generation."""

        from doubtbench.generate_split import main


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )
    write_text(
        OUT / "generate_surface_forms.py",
        '''
        #!/usr/bin/env python3
        """Entry point for answer-preserving surface-form generation."""

        from doubtbench.generate_surface_variants import main


        if __name__ == "__main__":
            main()
        ''',
    )
    write_text(
        OUT / "requirements.txt",
        '''
        accelerate>=0.34
        torch>=2.1
        transformers>=4.48
        ''',
    )

    write_text(
        OUT / "scripts/verify_artifact.py",
        '''
        #!/usr/bin/env python3
        """Verify the released task files, manifests, pairings, and result inventories."""

        from __future__ import annotations

        import csv
        import hashlib
        import json
        import sys
        from collections import Counter
        from pathlib import Path


        ROOT = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(ROOT))

        from doubtbench.scoring import score_output  # noqa: E402


        TASK_SETS = (
            "task_set_16061",
            "task_set_16101",
            "task_set_16102",
            "task_set_19003",
        )
        EXPECTED_FAMILIES = {
            "working_memory",
            "inhibition",
            "flexibility",
            "rule_learning",
            "monitoring",
            "planning",
            "relational_integration",
            "goal_management",
        }
        EXPECTED_MODELS = {
            "qwen2.5-7b",
            "mistral7b",
            "llama3.1-8b",
            "phi3.5-mini",
            "tulu3-sft-8b",
            "tulu3-dpo-8b",
        }


        def sha256(path: Path) -> str:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            return digest.hexdigest()


        def read_jsonl(path: Path) -> list[dict]:
            with path.open(encoding="utf-8") as handle:
                return [json.loads(line) for line in handle if line.strip()]


        def verify_main_tasks() -> set[str]:
            all_ids: set[str] = set()
            all_types: set[str] = set()
            for task_set in TASK_SETS:
                path = ROOT / "data" / f"{task_set}.jsonl"
                manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
                rows = read_jsonl(path)
                assert manifest["benchmark"] == "DoubtBench"
                assert manifest["task_count"] == len(rows) == 1600
                assert manifest["sha256"] == sha256(path)
                ids = [row["task_id"] for row in rows]
                assert len(ids) == len(set(ids))
                assert not (all_ids & set(ids))
                all_ids.update(ids)
                families = Counter(row["family"] for row in rows)
                difficulties = Counter(row["difficulty"] for row in rows)
                assert set(families) == EXPECTED_FAMILIES
                assert set(families.values()) == {200}
                assert difficulties == {"easy": 640, "medium": 640, "hard": 320}
                for row in rows:
                    assert row["dataset"] == "doubtbench"
                    assert score_output(f"Final answer: {row['gold']}", row["gold"], row["answer_type"])
                    all_types.add(row["task_type"])
            assert len(all_ids) == 6400
            assert len(all_types) == 33
            return all_ids


        def verify_surface(main_ids: set[str]) -> None:
            path = ROOT / "data" / "surface_forms.jsonl"
            manifest = json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
            rows = read_jsonl(path)
            assert manifest["sha256"] == sha256(path)
            assert manifest["latent_task_count"] == 330
            assert manifest["rendering_count"] == len(rows) == 990
            grouped: dict[str, list[dict]] = {}
            for row in rows:
                metadata = row["metadata"]["doubtbench"]
                assert metadata["main_task_id"] in main_ids
                grouped.setdefault(metadata["latent_task_id"], []).append(row)
            assert len(grouped) == 330
            for group in grouped.values():
                assert {row["metadata"]["doubtbench"]["surface_form"] for row in group} == {
                    "canonical",
                    "structured",
                    "scenario",
                }
                assert len({(row["gold"], row["answer_type"]) for row in group}) == 1


        def verify_results() -> None:
            required = {
                "scorecard_by_model.csv",
                "scorecard_by_model_seed.csv",
                "condition_accuracy_by_model.csv",
                "family_effects_by_model.csv",
                "difficulty_effects_by_model.csv",
                "surface_effects.csv",
                "surface_consistency.csv",
                "tulu_posttraining_case_study.csv",
            }
            assert required <= {path.name for path in (ROOT / "results").glob("*.csv")}
            with (ROOT / "results" / "scorecard_by_model.csv").open(newline="", encoding="utf-8") as handle:
                models = {row["model_slug"] for row in csv.DictReader(handle)}
            assert models == EXPECTED_MODELS


        def verify_public_surface() -> None:
            # Construct tokens so this file does not contain the forbidden literals.
            forbidden = [
                "_".join(("pair", "ctrl")),
                "".join(("pair", "ctrl")),
                "-".join(("PAIR", "CTRL")),
                "".join(("exp", "02")),
                "".join(("exp", "14")),
                "".join(("exp", "16")),
                "".join(("exp", "18")),
                "-".join(("EXP", "02")),
                "-".join(("EXP", "14")),
                "-".join(("EXP", "16")),
                "-".join(("EXP", "18")),
                "CAI" + "Sc",
                "-".join(("identity", "emotion")),
                "melanch" + "olic",
                "GSM" + "8K",
                "19003-" + "heldout",
                "inclusive_" + "scorecard",
                "load_" + "dotenv",
            ]
            for path in ROOT.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() in {".pdf", ".png", ".svg", ".jsonl"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for token in forbidden:
                    if token in text:
                        raise AssertionError(
                            f"Internal token {token!r} found in {path.relative_to(ROOT)}"
                        )


        def main() -> int:
            main_ids = verify_main_tasks()
            verify_surface(main_ids)
            verify_results()
            verify_public_surface()
            print("PASS: 6,400 unique tasks across four task sets")
            print("PASS: 330 latent surface tasks and 990 paired renderings")
            print("PASS: gold-answer self-checks and file hashes")
            print("PASS: compact result tables for six checkpoints")
            print("PASS: no internal package names in released text files")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        ''',
    )

    source = ROOT / "submissions/cods2026/paper/make_results_figures.py"
    destination = OUT / "scripts" / "make_results_figures.py"
    text = source.read_text(encoding="utf-8")
    text = text.replace(
        "Build publication-ready CODS result figures",
        "Build publication-ready DoubtBench result figures",
    )
    text = text.replace(
        'HERE = Path(__file__).resolve().parent\n'
        'ROOT = HERE.parents[2]\n'
        'ANALYSIS = ROOT / "submissions" / "cods2026" / "results" / "analysis" / "inclusive"\n'
        'FIG = HERE / "figures" / "results"',
        'HERE = Path(__file__).resolve().parent\n'
        'ROOT = HERE.parent\n'
        'ANALYSIS = ROOT / "results"\n'
        'FIG = ROOT / "figures"',
    )
    text = text.replace(
        'write_and_convert("inclusive_scorecard_heatmap", s)',
        'write_and_convert("scorecard_heatmap", s)',
    )
    if 'ANALYSIS = ROOT / "results"' not in text or "cods2026" in text or "inclusive_scorecard" in text:
        raise RuntimeError("Failed to retarget make_results_figures.py paths")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def copy_results() -> None:
    result_dir = OUT / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    drops = {
        "scorecard_by_model.csv": {"included_quality_flagged_cells", "included_mixed_budget_cells"},
        "scorecard_by_model_seed.csv": {"protocol_status", "diagnostic_status"},
        "condition_accuracy_by_model.csv": {"parse_failure_rate", "truncation_rate"},
    }
    names = (
        "scorecard_by_model.csv",
        "scorecard_by_model_seed.csv",
        "condition_accuracy_by_model.csv",
        "family_effects_by_model.csv",
        "difficulty_effects_by_model.csv",
        "surface_effects.csv",
        "surface_consistency.csv",
        "tulu_posttraining_case_study.csv",
    )
    for name in names:
        source = RESULT_SOURCE / name
        destination = result_dir / name
        with source.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = [
                field for field in (rows[0].keys() if rows else []) if field not in drops.get(name, set())
            ]
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                if name == "scorecard_by_model_seed.csv" and row.get("seed") == "19003-heldout":
                    row = dict(row)
                    row["seed"] = "19003"
                writer.writerow(row)
    write_text(
        result_dir / "README.md",
        '''
        # Result tables

        All accuracies and effects are stored as proportions; multiply by 100 for
        percent or percentage-point presentation.

        - `scorecard_by_model.csv`: primary checkpoint-level effects and paired
          bootstrap intervals.
        - `condition_accuracy_by_model.csv`: macro accuracy and mean generated length
          in every checkpoint, prompt-condition, and task-context cell.
        - `scorecard_by_model_seed.csv`: primary effects for each independently
          generated task set.
        - `family_effects_by_model.csv`: effects by checkpoint and task family.
        - `difficulty_effects_by_model.csv`: effects by checkpoint and generated
          difficulty.
        - `surface_effects.csv`: checking gain and Conditional Doubt Effect for each
          surface form and task context.
        - `surface_consistency.csv`: correctness agreement among the three surface
          forms for each checkpoint, condition, and task context.
        - `tulu_posttraining_case_study.csv`: within-lineage comparison of the Tulu SFT
          and DPO checkpoints.
        ''',
    )


def copy_figures() -> None:
    figure_dir = OUT / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    # Public figure names; rename analysis-jargon stems on copy.
    names = (
        ("cde_context_forest", "cde_context_forest"),
        ("inclusive_scorecard_heatmap", "scorecard_heatmap"),
        ("family_cde_heatmap", "family_cde_heatmap"),
        ("surface_cde_robustness", "surface_cde_robustness"),
        ("concision_accuracy_token_tradeoff", "concision_accuracy_token_tradeoff"),
    )
    for source_stem, dest_stem in names:
        for suffix in (".svg", ".pdf", ".png"):
            source = FIGURE_SOURCE / f"{source_stem}{suffix}"
            destination = figure_dir / f"{dest_stem}{suffix}"
            if not source.exists():
                alt = ROOT / "submissions/wsdm2027/supplementary/figures" / f"{source_stem}.pdf"
                if suffix == ".pdf" and alt.exists():
                    shutil.copy2(alt, destination)
                    continue
                raise FileNotFoundError(source)
            shutil.copy2(source, destination)


def emit_readme() -> None:
    write_text(
        OUT / "README.md",
        '''
        # DoubtBench code, data, and results

        This artifact accompanies *DoubtBench: Does Self-Doubt Help Language
        Models—or Just Make Them Check?* It contains the benchmark instances, the
        factorial evaluator and exact-answer scorer, the compact result tables used in
        the paper and supplementary material, and the code used to render the result
        figures.

        ## Contents

        - `data/`: four independently generated task sets (1,600 tasks each) and the
          paired surface-form set.
        - `run_factorial.py`: the command-line entry point for the full five-condition
          by two-context evaluation.
        - `generate_task_set.py` and `generate_surface_forms.py`: deterministic task
          and answer-preserving surface-form generators.
        - `doubtbench/`: task generators and exact-answer scorer.
        - `evaluation/`: Hugging Face runner, generation helpers, and factorial design.
        - `core/`: small shared I/O helpers.
        - `results/`: machine-readable checkpoint-, condition-, task-set-, family-,
          difficulty-, surface-, and post-training summaries.
        - `figures/`: the five result figures included with the supplementary material.
        - `scripts/make_results_figures.py`: deterministic figure-generation code.
        - `scripts/verify_artifact.py`: structural and numerical integrity checks.

        The archive intentionally omits model weights, caches, scheduler files, logs,
        and raw model completions. The included result CSV files are the compact
        statistics reported in the paper; the benchmark and evaluator are sufficient
        to produce new response records for any compatible causal language model.

        ## Verify the artifact

        Python 3.10 or later is required. The integrity check uses only the standard
        library and the included scorer:

        ```sh
        python scripts/verify_artifact.py
        ```

        A successful run reports 6,400 unique main tasks, 330 latent surface tasks,
        990 surface renderings, and six evaluated checkpoints in the result tables.

        ## Install inference dependencies

        Create an isolated environment and install:

        ```sh
        python -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        ```

        ## Run the factorial evaluation

        The following example evaluates one complete task set. Replace the model
        repository and batch size as appropriate for the available accelerator.

        ```sh
        python run_factorial.py \\
          --model Qwen/Qwen2.5-7B-Instruct \\
          --data-file data/task_set_16061.jsonl \\
          --out outputs/qwen_task_set_16061 \\
          --max-new-tokens 768 \\
          --batch-size 8
        ```

        The command uses greedy decoding and evaluates every task under five prompt
        conditions and two task contexts. It writes the full configuration, sampled
        tasks, raw responses, parsed responses, aggregate metrics, and CSV tables to
        the requested output directory. Use `--resume` to continue an interrupted run
        without regenerating completed task–condition–context cells.

        To evaluate the answer-preserving surface forms, pass
        `data/surface_forms.jsonl`. This file contains the canonical, structured, and
        scenario rendering of each of 330 latent tasks.

        ## Generate a new task set

        The generator derives an independent random stream for each family. This makes
        the output deterministic for a given task-set name and seed:

        ```sh
        python generate_task_set.py \\
          --split-id replication_24001 \\
          --seed 24001 \\
          --families all \\
          --per-family 200 \\
          --out data/replication_24001.jsonl
        ```

        To create the two additional surface forms from a complete task set:

        ```sh
        python generate_surface_forms.py \\
          --source data/replication_24001.jsonl \\
          --out data/replication_24001_surface_variants.jsonl
        ```

        ## Recreate the figures

        The figure script reads the included CSV tables and writes SVG, PDF, and PNG
        files to `figures/`:

        ```sh
        python scripts/make_results_figures.py
        ```

        It uses only the Python standard library for drawing and the external
        `rsvg-convert` command for PDF and PNG conversion.

        ## Evaluation protocol

        See `BENCHMARK.md` for the benchmark composition, exact prompt conditions,
        task contexts, outcome definitions, and the Conditional Doubt Effect.
        ''',
    )


def emit_benchmark_md(preserved: str | None) -> None:
    if not preserved:
        raise RuntimeError("BENCHMARK.md content was not preserved before rebuild")
    (OUT / "BENCHMARK.md").write_text(preserved, encoding="utf-8")


def write_zip() -> None:
    if ZIP_OUT.exists():
        ZIP_OUT.unlink()
    with zipfile.ZipFile(ZIP_OUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            archive.write(path, arcname=str(Path("DoubtBench_WSDM_Artifact") / path.relative_to(OUT)))


def main() -> None:
    if not all(path.exists() for path in TASK_SOURCES.values()):
        missing = [str(path) for path in TASK_SOURCES.values() if not path.exists()]
        raise SystemExit(f"Missing task sources: {missing}")
    if not SURFACE_SOURCE.exists():
        raise SystemExit(f"Missing surface source: {SURFACE_SOURCE}")
    if not RESULT_SOURCE.exists():
        raise SystemExit(f"Missing result source: {RESULT_SOURCE}")

    preserved_benchmark = None
    existing_benchmark = OUT / "BENCHMARK.md"
    if existing_benchmark.exists():
        preserved_benchmark = existing_benchmark.read_text(encoding="utf-8")
    elif (Path("/tmp/DoubtBench_BENCHMARK.md")).exists():
        preserved_benchmark = Path("/tmp/DoubtBench_BENCHMARK.md").read_text(encoding="utf-8")
    else:
        # Recover from the previously shipped zip if the directory was wiped.
        zip_path = ZIP_OUT
        if zip_path.exists():
            with zipfile.ZipFile(zip_path) as archive:
                preserved_benchmark = archive.read("DoubtBench_WSDM_Artifact/BENCHMARK.md").decode("utf-8")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    public_maps: dict[str, dict[str, str]] = {}
    cleaned_sets: dict[str, list[dict]] = {}
    for task_set, source in TASK_SOURCES.items():
        rows, public_map = clean_task_set(task_set, source)
        cleaned_sets[task_set] = rows
        public_maps[task_set] = public_map
        write_task_set(task_set, rows)
    surface_rows = clean_surface_rows(public_maps["task_set_19003"], cleaned_sets["task_set_19003"])
    write_surface(surface_rows)

    emit_core()
    emit_evaluation()
    emit_doubtbench_package()
    emit_wrappers_and_scripts()
    copy_results()
    copy_figures()
    emit_readme()
    emit_benchmark_md(preserved_benchmark)
    write_zip()
    print(f"Built {OUT}")
    print(f"Wrote {ZIP_OUT}")


if __name__ == "__main__":
    main()
