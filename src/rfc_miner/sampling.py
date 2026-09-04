from __future__ import annotations

import csv
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .io import read_jsonl, write_json
from .operation_linkage import (
    async_operation_paths_by_repo,
    async_resource_paths,
    cancellation_record_linkage,
    included_family_id,
)
from .paths import DataPaths, ensure_data_dirs


FULL_SAMPLE_SIZES = {
    "post-subresource-cancel": 80,
    "post-action-cancel": 50,
    "delete-action-cancel": 30,
    "put-action-cancel": 27,
    "get-cancel-link": 18,
    "patch-state-cancelled": 5,
    "delete-operation-resource": 50,
}

MINIMUM_SAMPLE_SIZES = {
    "post-subresource-cancel": 50,
    "post-action-cancel": 30,
    "delete-action-cancel": 20,
    "put-action-cancel": 15,
    "get-cancel-link": 10,
    "patch-state-cancelled": 5,
    "delete-operation-resource": 10,
}

PATTERN_ORDER = tuple(FULL_SAMPLE_SIZES)
BUCKET_ORDER = (
    "same-resource-linked",
    "operation-like-target",
    "domain-transition-risk",
    "other",
)

SAMPLE_COLUMNS = [
    "sample_id",
    "family_id",
    "repository",
    "pattern",
    "linkageBucket",
    "httpMethod",
    "normalizedPath",
    "path",
    "sourceKind",
    "file",
    "lineStart",
    "commit",
    "symbol",
    "responseCodes",
    "confidence",
    "cancelTargetPath",
    "routeLevelOperationLinked",
    "operationTarget",
    "domainTransitionRisk",
    "primaryLabel",
    "secondaryFlags",
    "reviewerConfidence",
    "rationale",
    "adjacentOperationEvidence",
    "terminalStateEvidence",
    "responseSemanticsEvidence",
    "reviewer",
    "adjudicatedLabel",
]


def write_cancellation_sample(
    *,
    paths: DataPaths,
    output_path: str | Path | None = None,
    profile: str = "full",
    seed: int = 20260904,
) -> tuple[Path, int]:
    ensure_data_dirs(paths)
    evidence = read_jsonl(paths.normalized_evidence)
    families = read_jsonl(paths.families)
    family_by_repo = {str(record.get("repo_id") or ""): record for record in families}
    rows = build_cancellation_sample_records(
        evidence=evidence,
        family_by_repo=family_by_repo,
        profile=profile,
        seed=seed,
    )

    target = Path(output_path) if output_path else paths.results_dir / "validation" / "http-cancellation-sample.csv"
    write_csv(target, rows)
    write_json(
        target.with_suffix(".summary.json"),
        sample_summary(rows),
    )
    return target, len(rows)


def build_cancellation_sample_records(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
    profile: str = "full",
    seed: int = 20260904,
) -> list[dict[str, str]]:
    sample_sizes = sample_size_profile(profile)
    async_paths_by_repo = async_operation_paths_by_repo(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    async_index = async_evidence_index(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    grouped: dict[str, dict[str, dict[str, list[dict[str, str]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for record in evidence:
        if str(record.get("concept") or "") != "http-cancellation":
            continue
        pattern = str(record.get("pattern") or "")
        if pattern not in sample_sizes:
            continue
        repo_id = str(record.get("repository") or "")
        family_id = included_family_id(repo_id, family_by_repo)
        if family_id is None:
            continue
        linkage = cancellation_record_linkage(
            record=record,
            async_paths_by_repo=async_paths_by_repo,
        )
        row = sample_row(
            record=record,
            family_id=family_id,
            linkage=linkage,
            adjacent_records=async_index.get((repo_id, linkage["cancelTargetPath"]), []),
        )
        grouped[pattern][row["linkageBucket"]][family_id].append(row)

    selected: list[dict[str, str]] = []
    repository_pattern_counts: Counter[tuple[str, str]] = Counter()
    repository_total_counts: Counter[str] = Counter()
    for pattern in PATTERN_ORDER:
        selected.extend(
            select_pattern_rows(
                pattern=pattern,
                bucketed_families=grouped.get(pattern, {}),
                target_size=sample_sizes[pattern],
                seed=seed,
                repository_pattern_counts=repository_pattern_counts,
                repository_total_counts=repository_total_counts,
            )
        )

    for index, row in enumerate(selected, start=1):
        row["sample_id"] = f"cancel-{index:04d}"
    return selected


def sample_size_profile(profile: str) -> dict[str, int]:
    if profile == "full":
        return dict(FULL_SAMPLE_SIZES)
    if profile == "minimum":
        return dict(MINIMUM_SAMPLE_SIZES)
    raise ValueError(f"unknown cancellation sample profile: {profile}")


def async_evidence_index(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in evidence:
        if str(record.get("concept") or "") != "http-async-operation":
            continue
        repo_id = str(record.get("repository") or "")
        if included_family_id(repo_id, family_by_repo) is None:
            continue
        for path in async_resource_paths(record):
            index[(repo_id, path)].append(record)
    return index


def select_pattern_rows(
    *,
    pattern: str,
    bucketed_families: dict[str, dict[str, list[dict[str, str]]]],
    target_size: int,
    seed: int,
    repository_pattern_counts: Counter[tuple[str, str]],
    repository_total_counts: Counter[str],
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    queues = shuffled_family_queues(
        pattern=pattern,
        bucketed_families=bucketed_families,
        seed=seed,
    )
    eligible_buckets = [bucket for bucket in BUCKET_ORDER if queues.get(bucket)]
    if not eligible_buckets:
        return selected

    quotas = balanced_quotas(target_size, eligible_buckets)
    for bucket in eligible_buckets:
        selected.extend(
            drain_bucket(
                pattern=pattern,
                queue=queues[bucket],
                target_size=quotas[bucket],
                repository_pattern_counts=repository_pattern_counts,
                repository_total_counts=repository_total_counts,
            )
        )

    while len(selected) < target_size:
        progress = False
        for bucket in eligible_buckets:
            if len(selected) >= target_size:
                break
            row = next_allowed_row(
                pattern=pattern,
                queue=queues[bucket],
                repository_pattern_counts=repository_pattern_counts,
                repository_total_counts=repository_total_counts,
            )
            if row is None:
                continue
            selected.append(row)
            progress = True
        if not progress:
            break

    return selected


def shuffled_family_queues(
    *,
    pattern: str,
    bucketed_families: dict[str, dict[str, list[dict[str, str]]]],
    seed: int,
) -> dict[str, list[list[dict[str, str]]]]:
    queues: dict[str, list[list[dict[str, str]]]] = {}
    for bucket, families in bucketed_families.items():
        family_ids = sorted(families)
        rng = random.Random(f"{seed}:{pattern}:{bucket}")
        rng.shuffle(family_ids)
        queues[bucket] = [sorted(families[family_id], key=row_quality_key) for family_id in family_ids]
    return queues


def balanced_quotas(target_size: int, buckets: list[str]) -> dict[str, int]:
    base = target_size // len(buckets)
    remainder = target_size % len(buckets)
    return {
        bucket: base + (1 if index < remainder else 0)
        for index, bucket in enumerate(buckets)
    }


def drain_bucket(
    *,
    pattern: str,
    queue: list[list[dict[str, str]]],
    target_size: int,
    repository_pattern_counts: Counter[tuple[str, str]],
    repository_total_counts: Counter[str],
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    while len(selected) < target_size:
        row = next_allowed_row(
            pattern=pattern,
            queue=queue,
            repository_pattern_counts=repository_pattern_counts,
            repository_total_counts=repository_total_counts,
        )
        if row is None:
            break
        selected.append(row)
    return selected


def next_allowed_row(
    *,
    pattern: str,
    queue: list[list[dict[str, str]]],
    repository_pattern_counts: Counter[tuple[str, str]],
    repository_total_counts: Counter[str],
) -> dict[str, str] | None:
    while queue:
        rows = queue.pop(0)
        for row in rows:
            repository = row["repository"]
            if repository_pattern_counts[(repository, pattern)] >= 2:
                continue
            if repository_total_counts[repository] >= 5:
                continue
            repository_pattern_counts[(repository, pattern)] += 1
            repository_total_counts[repository] += 1
            return row
    return None


def sample_row(
    *,
    record: dict[str, Any],
    family_id: str,
    linkage: dict[str, Any],
    adjacent_records: list[dict[str, Any]],
) -> dict[str, str]:
    response_codes = ",".join(str(code) for code in record.get("responseCodes") or [])
    return {
        "sample_id": "",
        "family_id": family_id,
        "repository": str(record.get("repository") or ""),
        "pattern": str(record.get("pattern") or ""),
        "linkageBucket": str(linkage.get("linkageBucket") or ""),
        "httpMethod": str(record.get("httpMethod") or ""),
        "normalizedPath": str(record.get("normalizedPath") or ""),
        "path": str(record.get("path") or ""),
        "sourceKind": str(record.get("sourceKind") or ""),
        "file": str(record.get("file") or ""),
        "lineStart": str(record.get("lineStart") or ""),
        "commit": str(record.get("commit") or ""),
        "symbol": str(record.get("symbol") or ""),
        "responseCodes": response_codes,
        "confidence": str(record.get("confidence") or ""),
        "cancelTargetPath": str(linkage.get("cancelTargetPath") or ""),
        "routeLevelOperationLinked": str(bool(linkage.get("routeLevelOperationLinked"))).lower(),
        "operationTarget": str(bool(linkage.get("operationTarget"))).lower(),
        "domainTransitionRisk": str(bool(linkage.get("domainTransitionRisk"))).lower(),
        "primaryLabel": "",
        "secondaryFlags": "",
        "reviewerConfidence": "",
        "rationale": "",
        "adjacentOperationEvidence": format_evidence(adjacent_records),
        "terminalStateEvidence": format_evidence(
            [record for record in adjacent_records if str(record.get("pattern") or "") == "get-status-resource"]
        ),
        "responseSemanticsEvidence": f"cancel response codes: {response_codes}" if response_codes else "",
        "reviewer": "",
        "adjudicatedLabel": "",
    }


def row_quality_key(row: dict[str, str]) -> tuple[int, int, int, float, str, int]:
    return (
        0 if row["routeLevelOperationLinked"] == "true" else 1,
        0 if row["sourceKind"] == "source" else 1,
        0 if "202" in row["responseCodes"].split(",") else 1,
        -safe_float(row["confidence"]),
        row["file"],
        safe_int(row["lineStart"]),
    )


def format_evidence(records: list[dict[str, Any]], *, limit: int = 3) -> str:
    fragments: list[str] = []
    for record in sorted(records, key=evidence_sort_key)[:limit]:
        fragments.append(
            "{method} {path} {pattern} {file}:{line}".format(
                method=record.get("httpMethod") or "",
                path=record.get("normalizedPath") or record.get("path") or "",
                pattern=record.get("pattern") or "",
                file=record.get("file") or "",
                line=record.get("lineStart") or "",
            )
        )
    return " | ".join(fragments)


def evidence_sort_key(record: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(record.get("pattern") or ""),
        str(record.get("file") or ""),
        safe_int(record.get("lineStart")),
    )


def sample_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_pattern = Counter(row["pattern"] for row in rows)
    by_bucket = Counter(row["linkageBucket"] for row in rows)
    return {
        "sampleCount": len(rows),
        "byPattern": dict(sorted(by_pattern.items())),
        "byLinkageBucket": dict(sorted(by_bucket.items())),
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SAMPLE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1_000_000
