from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Iterator


EXPECTED_SOURCE_COUNTS = {
    "train": 21_000,
    "validation": 4_500,
    "test": 4_500,
    "cross_domain": 1_000,
}

PUBLISHED_PROMPT = """You are a fraud detection expert. Analyze the following phone conversation against the given policies to determine if it contains fraudulent activity.

POLICIES:
{policy_text}

CONVERSATION:
{transcript_text}

TASK: Based on the policies above, is this conversation fraudulent?

Think step by step:
1. Identify any policy violations in the conversation
2. Look for pressure tactics, urgency, or requests for sensitive information
3. Consider if the agent is following legitimate procedures

Answer with only YES (fraudulent) or NO (legitimate), followed by a brief explanation.

ANSWER:"""

FALLBACK_POLICY = """Rule A: Agents must NEVER ask for passwords, PINs, OTPs, or other sensitive authentication information
Rule B: Agents must NEVER request immediate fund transfers or payments
Rule C: Agents must properly identify themselves and their organization
Rule D: Agents must NOT use high-pressure tactics or create false urgency
Rule E: Agents must NOT make unrealistic promises or guarantees"""


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_").lower()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def json_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _zstd_text_reader(path: Path) -> Iterator[str]:
    try:
        import zstandard as zstd

        with path.open("rb") as raw:
            with zstd.ZstdDecompressor().stream_reader(raw) as stream:
                with io.TextIOWrapper(stream, encoding="utf-8") as text:
                    yield from text
        return
    except ImportError:
        pass

    process = subprocess.Popen(
        ["zstd", "-dc", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdout is not None
    yield from process.stdout
    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"zstd failed for {path}: {stderr.strip()}")


def iter_json_records(path: Path) -> Iterator[dict]:
    if path.suffix == ".zst":
        lines: Iterable[str] = _zstd_text_reader(path)
    else:
        lines = path.open(encoding="utf-8")
    try:
        for line in lines:
            line = line.strip()
            if line:
                yield json.loads(line)
    finally:
        close = getattr(lines, "close", None)
        if close:
            close()


def source_shards(data_root: Path, split: str) -> list[Path]:
    source_root = data_root / "source_conversations"
    shards = sorted(source_root.glob(f"{split}-*.jsonl.zst"))
    if not shards:
        shards = sorted(source_root.glob(f"{split}-*.jsonl"))
    if not shards:
        raise FileNotFoundError(f"No source shards for split={split!r} below {source_root}")
    return shards


def load_release_source_split(data_root: Path, split: str, validate_count: bool = True) -> list[dict]:
    records = [record for shard in source_shards(data_root, split) for record in iter_json_records(shard)]
    expected = EXPECTED_SOURCE_COUNTS.get(split)
    if validate_count and expected is not None and len(records) != expected:
        raise ValueError(f"Expected {expected} {split} conversations, found {len(records)}")
    return records


def paper_main_splits(data_root: Path, seed: int = 42) -> dict[str, list[dict]]:
    """Rebuild the paper's stratified 70/15/15 split deterministically.

    The post-paper v1.0 upload shards used a domain/file-order partition that is
    not the stratified split implemented by the published RoBERTa code. We pool
    the same 30,000 conversations, sort by stable UID, then apply its two-stage
    seed-42 stratified split. This produces stable extension IDs and preserves
    the published split proportions and class balance.
    """
    from sklearn.model_selection import train_test_split

    records = []
    for release_split in ("train", "validation", "test"):
        records.extend(load_release_source_split(data_root, release_split))
    records.sort(key=lambda record: record_uid(record, "main", 0))
    labels = [binary_label(record) for record in records]
    train_val, test = train_test_split(
        records,
        test_size=0.15,
        random_state=seed,
        stratify=labels,
    )
    train_val_labels = [binary_label(record) for record in train_val]
    train, validation = train_test_split(
        train_val,
        test_size=0.15 / 0.85,
        random_state=seed,
        stratify=train_val_labels,
    )
    return {"train": train, "validation": validation, "test": test}


def paper_split_uid_map(data_root: Path, seed: int = 42) -> dict[str, str]:
    return {
        record_uid(record, split, index): split
        for split, records in paper_main_splits(data_root, seed).items()
        for index, record in enumerate(records)
    }


def load_source_split(data_root: Path, split: str, validate_count: bool = True, seed: int = 42) -> list[dict]:
    if split == "cross_domain":
        return load_release_source_split(data_root, split, validate_count)
    if split not in ("train", "validation", "test"):
        raise ValueError(f"Unknown source split: {split}")
    records = paper_main_splits(data_root, seed)[split]
    expected = EXPECTED_SOURCE_COUNTS[split]
    if validate_count and len(records) != expected:
        raise ValueError(f"Expected {expected} {split} conversations, found {len(records)}")
    return records


def transcript_to_text(record: dict) -> str:
    transcript = record.get("cumulative_transcript") or record.get("transcript") or []
    parts = []
    for turn in transcript:
        if not isinstance(turn, dict):
            continue
        speaker = turn.get("speaker", "Unknown")
        text = turn.get("text", "")
        parts.append(f"{speaker}: {text}")
    return "\n".join(parts)


def record_policy(record: dict) -> str:
    scenario = record.get("scenario") or record.get("scenario_info") or {}
    return scenario.get("policy") or FALLBACK_POLICY


def record_uid(record: dict, split: str, index: int) -> str:
    release = record.get("release_metadata") or {}
    return str(
        release.get("conversation_uid")
        or record.get("conversation_uid")
        or record.get("session_id")
        or f"{split}_{index:06d}"
    )


def binary_label(record: dict) -> int:
    label = str(record.get("final_verdict", "NO")).upper()
    return 1 if label == "YES" else 0


def published_prompt(record: dict) -> str:
    return PUBLISHED_PROMPT.format(
        policy_text=record_policy(record),
        transcript_text=transcript_to_text(record),
    )


def parse_yes_no(response: str) -> tuple[str, float, str]:
    stripped = response.strip()
    upper = stripped.upper()
    first_line = upper.splitlines()[0].strip() if upper else ""
    if re.fullmatch(r"YES(?:\s*\([^)]*\))?", first_line) or re.match(r"^YES\b(?!.*\bNO\b)", first_line):
        return "YES", 0.9, "prefix"
    if re.fullmatch(r"NO(?:\s*\([^)]*\))?", first_line) or re.match(r"^NO\b(?!.*\bYES\b)", first_line):
        return "NO", 0.9, "prefix"
    has_yes = bool(re.search(r"\bYES\b", upper))
    has_no = bool(re.search(r"\bNO\b", upper))
    if has_yes and not has_no:
        return "YES", 0.7, "fallback_unique_token"
    if has_no and not has_yes:
        return "NO", 0.7, "fallback_unique_token"
    return "NO", 0.3, "ambiguous_default_no"


def classification_metrics(labels: list[int], predictions: list[int]) -> dict:
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        precision_recall_fscore_support,
    )

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="binary", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
        "samples": len(labels),
        "positive_samples": int(sum(labels)),
    }
