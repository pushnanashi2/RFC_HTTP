from __future__ import annotations

import csv
import hashlib
import os
import random
import subprocess
import sys
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
    "post-action-cancel": 35,
    "delete-action-cancel": 31,
    "put-action-cancel": 27,
    "get-cancel-link": 18,
    "patch-state-cancelled": 5,
    "delete-operation-resource": 100,
}

FULL_ROUTE_SAMPLE_SIZES: dict[str, int | None] = {
    "delete-operation-resource:any": 100,
    "post-subresource-cancel:linked": 30,
    "post-subresource-cancel:unlinked": 70,
    "post-action-cancel:any": 50,
    "delete-action-cancel:any": None,
    "put-action-cancel:any": None,
    "get-cancel-link:any": None,
    "patch-state-cancelled:any": None,
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

MINIMUM_ROUTE_SAMPLE_SIZES: dict[str, int | None] = {
    "delete-operation-resource:any": 25,
    "post-subresource-cancel:linked": 15,
    "post-subresource-cancel:unlinked": 35,
    "post-action-cancel:any": 30,
    "delete-action-cancel:any": 20,
    "put-action-cancel:any": 15,
    "get-cancel-link:any": 10,
    "patch-state-cancelled:any": None,
}

PATTERN_ORDER = tuple(FULL_SAMPLE_SIZES)
ROUTE_STRATUM_ORDER = tuple(FULL_ROUTE_SAMPLE_SIZES)
STRICT_PATTERN_ORDER = tuple(pattern for pattern in PATTERN_ORDER if pattern != "delete-operation-resource")
STRICT_FAMILY_SAMPLE_SIZES = {
    "full": 140,
    "minimum": 80,
}
BUCKET_ORDER = (
    "mixed-same-resource-and-risk",
    "same-resource-linked",
    "mixed-operation-target-and-risk",
    "operation-like-target",
    "domain-transition-risk",
    "other",
)

SAMPLE_COLUMNS = [
    "sample_id",
    "route_id",
    "evidence_id",
    "samplingUnit",
    "estimationPopulation",
    "family_id",
    "repository",
    "pattern",
    "cellRouteCount",
    "linkageBucket",
    "populationFamilyMemberships",
    "patternSampleSize",
    "patternSamplingFraction",
    "analysisWeight",
    "familyPatternHasSameResourceLinked",
    "familyPatternHasOperationTarget",
    "familyPatternHasDomainTransitionRisk",
    "familyPatternCancellationEvidence",
    "strictFamilyPatternMemberships",
    "strictFamilyApproxInclusionProbability",
    "strictFamilyApproxAnalysisWeight",
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

FAMILY_SAMPLE_COLUMNS = [
    "sample_id",
    "route_id",
    "evidence_id",
    "samplingUnit",
    "estimationPopulation",
    "family_id",
    "repository",
    "pattern",
    "linkageBucket",
    "populationStrictFamilies",
    "strictFamilySampleSize",
    "strictFamilySamplingFraction",
    "strictFamilyAnalysisWeight",
    "strictFamilyPatternMemberships",
    "strictFamilyHasSameResourceLinked",
    "strictFamilyHasOperationTarget",
    "strictFamilyHasDomainTransitionRisk",
    "strictFamilyCancellationEvidence",
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

ROUTE_SAMPLE_COLUMNS = [
    "sample_id",
    "route_id",
    "evidence_id",
    "samplingUnit",
    "estimationPopulation",
    "routeStratum",
    "routeFramePopulationRecords",
    "routeStratumSampleSize",
    "routeStratumSamplingFraction",
    "routeStratumAnalysisWeight",
    "family_id",
    "repository",
    "pattern",
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
    "adjacentOperationEvidence",
    "terminalStateEvidence",
    "responseSemanticsEvidence",
    "primaryLabel",
    "secondaryFlags",
    "reviewerConfidence",
    "rationale",
    "reviewer",
    "adjudicatedLabel",
]

CELL_ROUTE_SAMPLE_COLUMNS = [
    "sample_id",
    "cell_sample_id",
    "cellRouteOrdinal",
    "route_id",
    "evidence_id",
    "samplingUnit",
    "estimationPopulation",
    "family_id",
    "repository",
    "pattern",
    "cellRouteCount",
    "linkageBucket",
    "populationFamilyMemberships",
    "patternSampleSize",
    "patternSamplingFraction",
    "analysisWeight",
    "familyPatternHasSameResourceLinked",
    "familyPatternHasOperationTarget",
    "familyPatternHasDomainTransitionRisk",
    "familyPatternCancellationEvidence",
    "strictFamilyPatternMemberships",
    "strictFamilyApproxInclusionProbability",
    "strictFamilyApproxAnalysisWeight",
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

LABELING_ID_COLUMNS = [
    "sample_id",
    "cell_sample_id",
    "cellRouteOrdinal",
    "route_id",
    "evidence_id",
]

LABELING_CONTEXT_COLUMNS = [
    "repository",
    "commit",
    "httpMethod",
    "normalizedPath",
    "path",
    "sourceKind",
    "file",
    "lineStart",
    "symbol",
    "responseCodes",
    "responseSemanticsEvidence",
]

LABELING_WORKFLOW_COLUMNS = [
    "unanchored_subset",
    "draft_visible_to_human",
    "draft_label",
    "draft_quote",
    "draft_rationale",
    "labeler_a_label",
    "labeler_a_quote",
    "labeler_a_rationale",
    "labeler_b_label",
    "labeler_b_quote",
    "labeler_b_rationale",
    "final_label",
    "adjudicator",
    "changed_from_draft",
    "note",
]

BLIND_LABELING_HIDDEN_COLUMNS = {
    "samplingUnit",
    "estimationPopulation",
    "pattern",
    "routeStratum",
    "linkageBucket",
    "cellRouteCount",
    "populationFamilyMemberships",
    "patternSampleSize",
    "patternSamplingFraction",
    "analysisWeight",
    "routeFramePopulationRecords",
    "routeStratumSampleSize",
    "routeStratumSamplingFraction",
    "routeStratumAnalysisWeight",
    "populationStrictFamilies",
    "strictFamilySampleSize",
    "strictFamilySamplingFraction",
    "strictFamilyAnalysisWeight",
    "familyPatternHasSameResourceLinked",
    "familyPatternHasOperationTarget",
    "familyPatternHasDomainTransitionRisk",
    "familyPatternCancellationEvidence",
    "strictFamilyPatternMemberships",
    "strictFamilyApproxInclusionProbability",
    "strictFamilyApproxAnalysisWeight",
    "strictFamilyHasSameResourceLinked",
    "strictFamilyHasOperationTarget",
    "strictFamilyHasDomainTransitionRisk",
    "strictFamilyCancellationEvidence",
    "confidence",
    "cancelTargetPath",
    "routeLevelOperationLinked",
    "operationTarget",
    "domainTransitionRisk",
    "adjacentOperationEvidence",
    "terminalStateEvidence",
    "primaryLabel",
    "secondaryFlags",
    "reviewerConfidence",
    "rationale",
    "reviewer",
    "adjudicatedLabel",
}


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
    write_csv(target, rows, columns=SAMPLE_COLUMNS)
    write_json(
        target.with_suffix(".summary.json"),
        sample_summary(rows, seed=seed, paths=paths),
    )
    return target, len(rows)


def write_cancellation_family_sample(
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
    rows = build_cancellation_family_sample_records(
        evidence=evidence,
        family_by_repo=family_by_repo,
        profile=profile,
        seed=seed,
    )

    target = (
        Path(output_path)
        if output_path
        else paths.results_dir / "validation" / "http-cancellation-family-sample.csv"
    )
    write_csv(target, rows, columns=FAMILY_SAMPLE_COLUMNS)
    write_json(
        target.with_suffix(".summary.json"),
        family_sample_summary(rows, seed=seed, paths=paths),
    )
    return target, len(rows)


def write_cancellation_route_sample(
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
    rows = build_cancellation_route_sample_records(
        evidence=evidence,
        family_by_repo=family_by_repo,
        profile=profile,
        seed=seed,
    )

    target = (
        Path(output_path)
        if output_path
        else paths.results_dir / "validation" / "http-cancellation-route-sample.csv"
    )
    write_csv(target, rows, columns=ROUTE_SAMPLE_COLUMNS)
    write_json(
        target.with_suffix(".summary.json"),
        route_sample_summary(rows, seed=seed, paths=paths),
    )
    return target, len(rows)


def write_cancellation_cell_route_sample(
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
    rows = build_cancellation_cell_route_sample_records(
        evidence=evidence,
        family_by_repo=family_by_repo,
        profile=profile,
        seed=seed,
    )

    target = (
        Path(output_path)
        if output_path
        else paths.results_dir / "validation" / "http-cancellation-cell-route-sample.csv"
    )
    write_csv(target, rows, columns=CELL_ROUTE_SAMPLE_COLUMNS)
    write_json(
        target.with_suffix(".summary.json"),
        cell_route_sample_summary(rows, seed=seed, paths=paths),
    )
    return target, len(rows)


def write_blind_labeling_views(
    *,
    input_path: str | Path,
    labeling_output_path: str | Path,
    machine_output_path: str | Path,
    seed: int = 20260904,
    unanchored_size: int = 80,
) -> tuple[Path, Path, int]:
    source = Path(input_path)
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    label_ids = sorted(row["sample_id"] for row in rows if row.get("sample_id"))
    rng = random.Random(f"{seed}:unanchored-subset:{source.name}")
    rng.shuffle(label_ids)
    unanchored_ids = set(label_ids[: min(unanchored_size, len(label_ids))])

    labeling_columns = [
        column
        for column in LABELING_ID_COLUMNS + LABELING_CONTEXT_COLUMNS
        if any(column in row for row in rows)
    ] + LABELING_WORKFLOW_COLUMNS
    machine_columns = [
        column
        for column in LABELING_ID_COLUMNS + fieldnames
        if column in fieldnames and (column in LABELING_ID_COLUMNS or column not in labeling_columns)
    ]
    machine_columns = list(dict.fromkeys(machine_columns))

    labeling_rows: list[dict[str, str]] = []
    machine_rows: list[dict[str, str]] = []
    for row in rows:
        sample_id = row.get("sample_id", "")
        labeling_row = {column: row.get(column, "") for column in labeling_columns}
        labeling_row.update(
            {
                "unanchored_subset": str(sample_id in unanchored_ids).lower(),
                "draft_visible_to_human": str(sample_id not in unanchored_ids).lower(),
                "draft_label": "",
                "draft_quote": "",
                "draft_rationale": "",
                "labeler_a_label": "",
                "labeler_a_quote": "",
                "labeler_a_rationale": "",
                "labeler_b_label": "",
                "labeler_b_quote": "",
                "labeler_b_rationale": "",
                "final_label": "",
                "adjudicator": "",
                "changed_from_draft": "",
                "note": "",
            }
        )
        labeling_rows.append(labeling_row)
        machine_rows.append({column: row.get(column, "") for column in machine_columns})

    labeling_target = Path(labeling_output_path)
    machine_target = Path(machine_output_path)
    write_csv(labeling_target, labeling_rows, columns=labeling_columns)
    write_csv(machine_target, machine_rows, columns=machine_columns)
    return labeling_target, machine_target, len(rows)


def build_cancellation_sample_records(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
    profile: str = "full",
    seed: int = 20260904,
) -> list[dict[str, str]]:
    sample_sizes = sample_size_profile(profile)
    rows_by_pattern_family, strict_patterns_by_family = cancellation_rows_by_pattern_family(
        evidence=evidence,
        family_by_repo=family_by_repo,
        patterns=set(sample_sizes),
    )
    return select_family_pattern_sample(
        rows_by_pattern_family=rows_by_pattern_family,
        strict_patterns_by_family=strict_patterns_by_family,
        sample_sizes=sample_sizes,
        seed=seed,
    )


def build_cancellation_cell_route_sample_records(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
    profile: str = "full",
    seed: int = 20260904,
) -> list[dict[str, str]]:
    sample_sizes = sample_size_profile(profile)
    rows_by_pattern_family, strict_patterns_by_family = cancellation_rows_by_pattern_family(
        evidence=evidence,
        family_by_repo=family_by_repo,
        patterns=set(sample_sizes),
    )
    selected_cells = select_family_pattern_sample(
        rows_by_pattern_family=rows_by_pattern_family,
        strict_patterns_by_family=strict_patterns_by_family,
        sample_sizes=sample_sizes,
        seed=seed,
    )

    expanded_rows: list[dict[str, str]] = []
    for cell_row in selected_cells:
        cell_rows = sorted(
            rows_by_pattern_family[cell_row["pattern"]][cell_row["family_id"]],
            key=row_quality_key,
        )
        for ordinal, route_row in enumerate(cell_rows, start=1):
            expanded = dict(route_row)
            for column in SAMPLE_COLUMNS:
                if column in {
                    "sample_id",
                    "route_id",
                    "evidence_id",
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
                    "adjacentOperationEvidence",
                    "terminalStateEvidence",
                    "responseSemanticsEvidence",
                    "primaryLabel",
                    "secondaryFlags",
                    "reviewerConfidence",
                    "rationale",
                    "reviewer",
                    "adjudicatedLabel",
                }:
                    continue
                expanded[column] = cell_row[column]
            expanded.update(
                {
                    "sample_id": f"{cell_row['sample_id']}-route-{ordinal:03d}",
                    "cell_sample_id": cell_row["sample_id"],
                    "cellRouteOrdinal": str(ordinal),
                    "samplingUnit": "family-pattern-cell-route",
                    "cellRouteCount": cell_row["cellRouteCount"],
                    "linkageBucket": cell_row["linkageBucket"],
                }
            )
            expanded_rows.append(expanded)
    return expanded_rows


def cancellation_rows_by_pattern_family(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
    patterns: set[str],
) -> tuple[dict[str, dict[str, list[dict[str, str]]]], dict[str, set[str]]]:
    async_paths_by_repo = async_operation_paths_by_repo(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    async_index = async_evidence_index(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    rows_by_pattern_family: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))

    for record in evidence:
        if str(record.get("concept") or "") != "http-cancellation":
            continue
        pattern = str(record.get("pattern") or "")
        if pattern not in patterns:
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
        rows_by_pattern_family[pattern][family_id].append(row)

    return rows_by_pattern_family, strict_pattern_memberships_by_family(rows_by_pattern_family)


def select_family_pattern_sample(
    *,
    rows_by_pattern_family: dict[str, dict[str, list[dict[str, str]]]],
    strict_patterns_by_family: dict[str, set[str]],
    sample_sizes: dict[str, int],
    seed: int,
) -> list[dict[str, str]]:
    grouped = group_family_pattern_representatives(rows_by_pattern_family, seed=seed)
    selected: list[dict[str, str]] = []
    repository_pattern_counts: Counter[tuple[str, str]] = Counter()
    repository_total_counts: Counter[str] = Counter()
    for pattern in PATTERN_ORDER:
        if pattern not in sample_sizes:
            continue
        selected.extend(
            select_pattern_rows(
                pattern=pattern,
                bucketed_families=grouped.get(pattern, {}),
                target_size=sample_sizes[pattern],
                population_family_memberships=len(rows_by_pattern_family.get(pattern, {})),
                seed=seed,
                repository_pattern_counts=repository_pattern_counts,
                repository_total_counts=repository_total_counts,
            )
        )

    for index, row in enumerate(selected, start=1):
        row["sample_id"] = f"cancel-{index:04d}"
    add_sampling_weights(selected, strict_patterns_by_family=strict_patterns_by_family)
    return selected


def build_cancellation_route_sample_records(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
    profile: str = "full",
    seed: int = 20260904,
) -> list[dict[str, str]]:
    sample_sizes = route_sample_size_profile(profile)
    async_paths_by_repo = async_operation_paths_by_repo(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    async_index = async_evidence_index(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    rows_by_stratum: dict[str, list[dict[str, str]]] = defaultdict(list)

    for record in evidence:
        if str(record.get("concept") or "") != "http-cancellation":
            continue
        pattern = str(record.get("pattern") or "")
        repo_id = str(record.get("repository") or "")
        family_id = included_family_id(repo_id, family_by_repo)
        if family_id is None:
            continue
        linkage = cancellation_record_linkage(
            record=record,
            async_paths_by_repo=async_paths_by_repo,
        )
        stratum = route_sample_stratum(pattern=pattern, linkage=linkage)
        if stratum not in sample_sizes:
            continue
        row = sample_row(
            record=record,
            family_id=family_id,
            linkage=linkage,
            adjacent_records=async_index.get((repo_id, linkage["cancelTargetPath"]), []),
        )
        row.update(
            {
                "samplingUnit": "route-record",
                "estimationPopulation": "route-cancellation-record",
                "routeStratum": stratum,
                "routeFramePopulationRecords": "",
                "routeStratumSampleSize": "",
                "routeStratumSamplingFraction": "",
                "routeStratumAnalysisWeight": "",
            }
        )
        rows_by_stratum[stratum].append(row)

    selected: list[dict[str, str]] = []
    for stratum in ROUTE_STRATUM_ORDER:
        selected.extend(
            select_route_stratum_rows(
                stratum=stratum,
                rows=rows_by_stratum.get(stratum, []),
                target_size=sample_sizes[stratum],
                seed=seed,
            )
        )

    for index, row in enumerate(selected, start=1):
        row["sample_id"] = f"cancel-route-{index:04d}"
    return selected


def build_cancellation_family_sample_records(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
    profile: str = "full",
    seed: int = 20260904,
) -> list[dict[str, str]]:
    target_size = strict_family_sample_size(profile)
    async_paths_by_repo = async_operation_paths_by_repo(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    async_index = async_evidence_index(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    rows_by_family: dict[str, list[dict[str, str]]] = defaultdict(list)

    for record in evidence:
        if str(record.get("concept") or "") != "http-cancellation":
            continue
        if str(record.get("pattern") or "") not in STRICT_PATTERN_ORDER:
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
        rows_by_family[family_id].append(row)

    family_rows = [
        strict_family_representative(family_id, rows, seed=seed)
        for family_id, rows in rows_by_family.items()
    ]
    family_rows.sort(key=lambda row: row["family_id"])
    rng = random.Random(f"{seed}:strict-cancellation-family")
    rng.shuffle(family_rows)
    selected = family_rows[: min(target_size, len(family_rows))]
    population_count = len(family_rows)
    sample_count = len(selected)

    for index, row in enumerate(selected, start=1):
        row["sample_id"] = f"cancel-family-{index:04d}"
        row["populationStrictFamilies"] = str(population_count)
        row["strictFamilySampleSize"] = str(sample_count)
        row["strictFamilySamplingFraction"] = format_ratio(sample_count, population_count)
        row["strictFamilyAnalysisWeight"] = format_float(population_count / sample_count if sample_count else 0.0)
    return selected


def sample_size_profile(profile: str) -> dict[str, int]:
    if profile == "full":
        return dict(FULL_SAMPLE_SIZES)
    if profile == "minimum":
        return dict(MINIMUM_SAMPLE_SIZES)
    raise ValueError(f"unknown cancellation sample profile: {profile}")


def route_sample_size_profile(profile: str) -> dict[str, int | None]:
    if profile == "full":
        return dict(FULL_ROUTE_SAMPLE_SIZES)
    if profile == "minimum":
        return dict(MINIMUM_ROUTE_SAMPLE_SIZES)
    raise ValueError(f"unknown cancellation route sample profile: {profile}")


def strict_family_sample_size(profile: str) -> int:
    try:
        return STRICT_FAMILY_SAMPLE_SIZES[profile]
    except KeyError as error:
        raise ValueError(f"unknown cancellation family sample profile: {profile}") from error


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


def group_family_pattern_representatives(
    rows_by_pattern_family: dict[str, dict[str, list[dict[str, str]]]],
    *,
    seed: int,
) -> dict[str, dict[str, dict[str, list[dict[str, str]]]]]:
    grouped: dict[str, dict[str, dict[str, list[dict[str, str]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for pattern, family_rows in rows_by_pattern_family.items():
        for family_id, rows in family_rows.items():
            has_same_resource = any(row["routeLevelOperationLinked"] == "true" for row in rows)
            has_operation_target = any(row["operationTarget"] == "true" for row in rows)
            has_domain_risk = any(row["domainTransitionRisk"] == "true" for row in rows)
            representative = select_cell_representative(
                family_id=family_id,
                pattern=pattern,
                rows=rows,
                seed=seed,
            )
            representative["cellRouteCount"] = str(len(rows))
            representative["linkageBucket"] = family_pattern_bucket(
                has_same_resource=has_same_resource,
                has_operation_target=has_operation_target,
                has_domain_risk=has_domain_risk,
            )
            representative["familyPatternHasSameResourceLinked"] = str(has_same_resource).lower()
            representative["familyPatternHasOperationTarget"] = str(has_operation_target).lower()
            representative["familyPatternHasDomainTransitionRisk"] = str(has_domain_risk).lower()
            representative["familyPatternCancellationEvidence"] = format_sample_row_evidence(rows)
            grouped[pattern][representative["linkageBucket"]][family_id].append(representative)
    return grouped


def strict_pattern_memberships_by_family(
    rows_by_pattern_family: dict[str, dict[str, list[dict[str, str]]]],
) -> dict[str, set[str]]:
    memberships: dict[str, set[str]] = defaultdict(set)
    for pattern in STRICT_PATTERN_ORDER:
        for family_id in rows_by_pattern_family.get(pattern, {}):
            memberships[family_id].add(pattern)
    return memberships


def strict_family_representative(
    family_id: str,
    rows: list[dict[str, str]],
    *,
    seed: int,
) -> dict[str, str]:
    has_same_resource = any(row["routeLevelOperationLinked"] == "true" for row in rows)
    has_operation_target = any(row["operationTarget"] == "true" for row in rows)
    has_domain_risk = any(row["domainTransitionRisk"] == "true" for row in rows)
    patterns = {row["pattern"] for row in rows}
    representative = select_cell_representative(
        family_id=family_id,
        pattern="strict-cancellation-family",
        rows=rows,
        seed=seed,
    )
    representative.update(
        {
            "sample_id": "",
            "samplingUnit": "strict-cancellation-family",
            "estimationPopulation": "strict-cancellation-family",
            "linkageBucket": family_pattern_bucket(
                has_same_resource=has_same_resource,
                has_operation_target=has_operation_target,
                has_domain_risk=has_domain_risk,
            ),
            "populationStrictFamilies": "",
            "strictFamilySampleSize": "",
            "strictFamilySamplingFraction": "",
            "strictFamilyAnalysisWeight": "",
            "strictFamilyPatternMemberships": ",".join(
                pattern for pattern in STRICT_PATTERN_ORDER if pattern in patterns
            ),
            "strictFamilyHasSameResourceLinked": str(has_same_resource).lower(),
            "strictFamilyHasOperationTarget": str(has_operation_target).lower(),
            "strictFamilyHasDomainTransitionRisk": str(has_domain_risk).lower(),
            "strictFamilyCancellationEvidence": format_sample_row_evidence(rows, limit=10),
        }
    )
    return representative


def family_pattern_bucket(
    *,
    has_same_resource: bool,
    has_operation_target: bool,
    has_domain_risk: bool,
) -> str:
    if has_same_resource and has_domain_risk:
        return "mixed-same-resource-and-risk"
    if has_same_resource:
        return "same-resource-linked"
    if has_operation_target and has_domain_risk:
        return "mixed-operation-target-and-risk"
    if has_operation_target:
        return "operation-like-target"
    if has_domain_risk:
        return "domain-transition-risk"
    return "other"


def select_pattern_rows(
    *,
    pattern: str,
    bucketed_families: dict[str, dict[str, list[dict[str, str]]]],
    target_size: int,
    population_family_memberships: int,
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
                population_family_memberships=population_family_memberships,
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
                population_family_memberships=population_family_memberships,
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
    population_family_memberships: int,
    repository_pattern_counts: Counter[tuple[str, str]],
    repository_total_counts: Counter[str],
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    while len(selected) < target_size:
        row = next_allowed_row(
            pattern=pattern,
            queue=queue,
            population_family_memberships=population_family_memberships,
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
    population_family_memberships: int,
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
            row["populationFamilyMemberships"] = str(population_family_memberships)
            row["estimationPopulation"] = estimation_population(pattern)
            return row
    return None


def select_route_stratum_rows(
    *,
    stratum: str,
    rows: list[dict[str, str]],
    target_size: int | None,
    seed: int,
) -> list[dict[str, str]]:
    population_count = len(rows)
    if population_count == 0:
        return []
    target_count = population_count if target_size is None else min(target_size, population_count)
    candidates = sorted(rows, key=route_sample_key)
    rng = random.Random(f"{seed}:route-record:{stratum}")
    rng.shuffle(candidates)
    selected = candidates[:target_count]
    for row in selected:
        row["routeFramePopulationRecords"] = str(population_count)
        row["routeStratumSampleSize"] = str(target_count)
        row["routeStratumSamplingFraction"] = format_ratio(target_count, population_count)
        row["routeStratumAnalysisWeight"] = format_float(
            population_count / target_count if target_count else 0.0
        )
    return selected


def sample_row(
    *,
    record: dict[str, Any],
    family_id: str,
    linkage: dict[str, Any],
    adjacent_records: list[dict[str, Any]],
) -> dict[str, str]:
    response_codes = ",".join(str(code) for code in record.get("responseCodes") or [])
    route_id = stable_route_id(record)
    return {
        "sample_id": "",
        "route_id": route_id,
        "evidence_id": stable_evidence_id(record, route_id=route_id),
        "samplingUnit": "family-pattern-representative",
        "estimationPopulation": "",
        "family_id": family_id,
        "repository": str(record.get("repository") or ""),
        "pattern": str(record.get("pattern") or ""),
        "cellRouteCount": "",
        "linkageBucket": str(linkage.get("linkageBucket") or ""),
        "populationFamilyMemberships": "",
        "patternSampleSize": "",
        "patternSamplingFraction": "",
        "analysisWeight": "",
        "familyPatternHasSameResourceLinked": str(bool(linkage.get("routeLevelOperationLinked"))).lower(),
        "familyPatternHasOperationTarget": str(bool(linkage.get("operationTarget"))).lower(),
        "familyPatternHasDomainTransitionRisk": str(bool(linkage.get("domainTransitionRisk"))).lower(),
        "familyPatternCancellationEvidence": "",
        "strictFamilyPatternMemberships": "",
        "strictFamilyApproxInclusionProbability": "",
        "strictFamilyApproxAnalysisWeight": "",
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


def add_sampling_weights(
    rows: list[dict[str, str]],
    *,
    strict_patterns_by_family: dict[str, set[str]] | None = None,
) -> None:
    sample_counts = Counter(row["pattern"] for row in rows)
    population_counts = {
        pattern: safe_int(next(row["populationFamilyMemberships"] for row in rows if row["pattern"] == pattern))
        for pattern in sample_counts
    }
    pattern_fractions = {
        pattern: sample_counts[pattern] / population_counts[pattern]
        for pattern in sample_counts
        if population_counts[pattern] > 0
    }
    for row in rows:
        sample_count = sample_counts[row["pattern"]]
        population_count = safe_int(row["populationFamilyMemberships"])
        row["patternSampleSize"] = str(sample_count)
        row["patternSamplingFraction"] = format_ratio(sample_count, population_count)
        row["analysisWeight"] = format_ratio(population_count, sample_count)
        if row["estimationPopulation"] != "strict-cancellation" or strict_patterns_by_family is None:
            continue
        memberships = [
            pattern
            for pattern in STRICT_PATTERN_ORDER
            if pattern in strict_patterns_by_family.get(row["family_id"], set())
        ]
        row["strictFamilyPatternMemberships"] = ",".join(memberships)
        inclusion_probability = family_inclusion_probability(memberships, pattern_fractions)
        row["strictFamilyApproxInclusionProbability"] = format_float(inclusion_probability)
        row["strictFamilyApproxAnalysisWeight"] = format_float(
            1 / inclusion_probability if inclusion_probability else 0.0
        )


def estimation_population(pattern: str) -> str:
    if pattern == "delete-operation-resource":
        return "delete-operation-resource-audit"
    return "strict-cancellation"


def route_sample_stratum(*, pattern: str, linkage: dict[str, Any]) -> str:
    if pattern == "post-subresource-cancel":
        suffix = "linked" if linkage.get("routeLevelOperationLinked") else "unlinked"
        return f"{pattern}:{suffix}"
    return f"{pattern}:any"


def select_cell_representative(
    *,
    family_id: str,
    pattern: str,
    rows: list[dict[str, str]],
    seed: int,
) -> dict[str, str]:
    candidates = sorted(rows, key=row_quality_key)
    rng = random.Random(f"{seed}:cell-route:{pattern}:{family_id}")
    return dict(candidates[rng.randrange(len(candidates))])


def row_quality_key(row: dict[str, str]) -> tuple[str, str, str, str, str, str, int, str, str]:
    return (
        row["repository"],
        row["pattern"],
        row["httpMethod"],
        row["normalizedPath"],
        row["path"],
        row["sourceKind"],
        safe_int(row["lineStart"]),
        row["file"],
        row["evidence_id"],
    )


def route_sample_key(row: dict[str, str]) -> tuple[str, str, str, str, int]:
    return (
        row["repository"],
        row["pattern"],
        row["normalizedPath"],
        row["file"],
        safe_int(row["lineStart"]),
    )


def stable_route_id(record: dict[str, Any]) -> str:
    return stable_digest(
        [
            record.get("repository"),
            record.get("httpMethod"),
            record.get("normalizedPath") or record.get("path"),
        ]
    )


def stable_evidence_id(record: dict[str, Any], *, route_id: str) -> str:
    return stable_digest(
        [
            route_id,
            record.get("commit"),
            record.get("pattern"),
            record.get("sourceKind"),
            record.get("path"),
            record.get("file"),
            record.get("lineStart"),
            record.get("symbol"),
        ]
    )


def stable_digest(parts: list[Any]) -> str:
    payload = "\x1f".join(str(part or "") for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def format_sample_row_evidence(rows: list[dict[str, str]], *, limit: int = 5) -> str:
    fragments = [
        "{method} {path} {bucket} {file}:{line}".format(
            method=row["httpMethod"],
            path=row["normalizedPath"],
            bucket=sample_row_route_bucket(row),
            file=row["file"],
            line=row["lineStart"],
        )
        for row in sorted(rows, key=row_quality_key)[:limit]
    ]
    if len(rows) > limit:
        fragments.append(f"... +{len(rows) - limit} more")
    return " | ".join(fragments)


def family_inclusion_probability(memberships: list[str], pattern_fractions: dict[str, float]) -> float:
    missed_probability = 1.0
    for pattern in memberships:
        missed_probability *= 1 - pattern_fractions.get(pattern, 0.0)
    return 1 - missed_probability


def sample_row_route_bucket(row: dict[str, str]) -> str:
    if row["routeLevelOperationLinked"] == "true":
        return "same-resource-linked"
    if row["operationTarget"] == "true":
        return "operation-like-target"
    if row["domainTransitionRisk"] == "true":
        return "domain-transition-risk"
    return "other"


def evidence_sort_key(record: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(record.get("pattern") or ""),
        str(record.get("file") or ""),
        safe_int(record.get("lineStart")),
    )


def sample_summary(rows: list[dict[str, str]], *, seed: int, paths: DataPaths) -> dict[str, Any]:
    by_pattern = Counter(row["pattern"] for row in rows)
    by_bucket = Counter(row["linkageBucket"] for row in rows)
    by_population = Counter(row["estimationPopulation"] for row in rows)
    by_source_kind = Counter(row["sourceKind"] for row in rows)
    by_source_kind_pattern: dict[str, dict[str, int]] = defaultdict(dict)
    for (source_kind, pattern), count in sorted(
        Counter((row["sourceKind"], row["pattern"]) for row in rows).items()
    ):
        by_source_kind_pattern[source_kind][pattern] = count
    cell_route_counts = [
        safe_int(row["cellRouteCount"])
        for row in rows
        if row.get("cellRouteCount")
    ]
    population_by_pattern = {
        pattern: safe_int(next(row["populationFamilyMemberships"] for row in rows if row["pattern"] == pattern))
        for pattern in by_pattern
    }
    return {
        "samplingUnit": "family-pattern-representative",
        "sampleCount": len(rows),
        "byPattern": dict(sorted(by_pattern.items())),
        "byLinkageBucket": dict(sorted(by_bucket.items())),
        "byEstimationPopulation": dict(sorted(by_population.items())),
        "bySourceKind": dict(sorted(by_source_kind.items())),
        "bySourceKindByPattern": {
            source_kind: dict(sorted(patterns.items()))
            for source_kind, patterns in sorted(by_source_kind_pattern.items())
        },
        "cellRouteCounts": {
            "selectedCells": len(cell_route_counts),
            "selectedRouteRecords": sum(cell_route_counts),
            "extraRouteLabelsIfClusterCensus": sum(cell_route_counts) - len(cell_route_counts),
            "distribution": {
                str(count): frequency
                for count, frequency in sorted(Counter(cell_route_counts).items())
            },
        },
        "populationFamilyMembershipsByPattern": dict(sorted(population_by_pattern.items())),
        "selectionProvenance": {
            **sampling_provenance(paths=paths, seed=seed),
            "seed": seed,
            "familyPatternRepresentative": (
                "Uniform pseudo-random route selection within each family_id x pattern cell "
                "after stable identity sorting. Automated linkage, HTTP 202 responses, "
                "source kind, and confidence are not used as preferential keys."
            ),
            "cellRouteSeedNamespace": "{seed}:cell-route:{pattern}:{family_id}",
            "familyQueueSeedNamespace": "{seed}:{pattern}:{bucket}",
            "routeId": "sha256(repository, httpMethod, normalizedPath-or-path)",
            "evidenceId": "sha256(route_id, commit, pattern, sourceKind, path, file, lineStart, symbol)",
        },
        "estimationGuidance": {
            "doNotPoolRawRows": True,
            "strictCancellation": (
                "Compute per-pattern rates and a pattern-family weighted estimate "
                "using populationFamilyMemberships. This estimates pattern-family "
                "membership precision, not unique-family prevalence over 407 families."
            ),
            "strictFamilySensitivity": (
                "strictFamilyApproxInclusionProbability gives a collapse-to-family sensitivity "
                "check using 1 - product(1 - patternSamplingFraction). Treat it as exploratory "
                "because bucket quotas and repository caps make the exact design probability "
                "more complex."
            ),
            "deleteOperationResource": (
                "Report separately as an audit stratum for possible strict-rule promotion; "
                "do not mix it into strict-cancellation estimates."
            ),
            "ambiguous": (
                "Report ambiguous-as-false-positive and ambiguous-as-true-positive bounds, "
                "plus an explicit non-ambiguous rate."
            ),
            "confidenceIntervals": (
                "Use Clopper-Pearson intervals as the primary interval for sampled strata, "
                "add finite-population corrected Wilson intervals as a secondary sensitivity "
                "view where applicable, and mark full-census strata separately."
            ),
        },
    }


def family_sample_summary(rows: list[dict[str, str]], *, seed: int, paths: DataPaths) -> dict[str, Any]:
    by_pattern_count = Counter(str(len(row["strictFamilyPatternMemberships"].split(","))) for row in rows)
    by_bucket = Counter(row["linkageBucket"] for row in rows)
    population_count = safe_int(rows[0]["populationStrictFamilies"]) if rows else 0
    sample_count = len(rows)
    return {
        "samplingUnit": "strict-cancellation-family",
        "estimationPopulation": "strict-cancellation-family",
        "sampleCount": sample_count,
        "populationStrictFamilies": population_count,
        "samplingFraction": format_ratio(sample_count, population_count),
        "analysisWeight": format_float(population_count / sample_count if sample_count else 0.0),
        "byLinkageBucket": dict(sorted(by_bucket.items())),
        "byStrictFamilyPatternMembershipCount": dict(sorted(by_pattern_count.items())),
        "selectionProvenance": {
            **sampling_provenance(paths=paths, seed=seed),
            "seed": seed,
            "familyRepresentative": (
                "Uniform pseudo-random route selection within each strict family after stable "
                "identity sorting; automated linkage and HTTP 202 responses are not preferential keys."
            ),
            "familyRouteSeedNamespace": "{seed}:cell-route:strict-cancellation-family:{family_id}",
            "routeId": "sha256(repository, httpMethod, normalizedPath-or-path)",
            "evidenceId": "sha256(route_id, commit, pattern, sourceKind, path, file, lineStart, symbol)",
        },
        "estimationGuidance": {
            "purpose": (
                "Use this sheet, not the pattern-family sheet, when updating unique-family "
                "claims over the 407 strict cancellation families."
            ),
            "primaryLabel": (
                "Label whether the family exposes at least one operation-cancellation affordance "
                "among strict cancellation evidence."
            ),
            "confidenceIntervals": (
                "Use a finite-population corrected interval for the simple random sample. "
                "Report labeling disagreement separately."
            ),
            "mixedFamilies": (
                "Inspect strictFamilyCancellationEvidence because a family can contain both "
                "operation cancellation and business cancellation routes."
            ),
        },
    }


def route_sample_summary(rows: list[dict[str, str]], *, seed: int, paths: DataPaths) -> dict[str, Any]:
    by_stratum = Counter(row["routeStratum"] for row in rows)
    by_pattern = Counter(row["pattern"] for row in rows)
    by_linkage = Counter("linked" if row["routeLevelOperationLinked"] == "true" else "unlinked" for row in rows)
    population_by_stratum = {
        stratum: safe_int(next(row["routeFramePopulationRecords"] for row in rows if row["routeStratum"] == stratum))
        for stratum in by_stratum
    }
    return {
        "samplingUnit": "route-record",
        "estimationPopulation": "route-cancellation-record",
        "sampleCount": len(rows),
        "byRouteStratum": dict(sorted(by_stratum.items())),
        "byPattern": dict(sorted(by_pattern.items())),
        "byRouteLevelLinkage": dict(sorted(by_linkage.items())),
        "populationRouteRecordsByStratum": dict(sorted(population_by_stratum.items())),
        "selectionProvenance": {
            **sampling_provenance(paths=paths, seed=seed),
            "seed": seed,
            "routeRecordSelection": "Uniform pseudo-random route selection within each exclusive route stratum.",
            "routeRecordSeedNamespace": "{seed}:route-record:{stratum}",
            "routeId": "sha256(repository, httpMethod, normalizedPath-or-path)",
            "evidenceId": "sha256(route_id, commit, pattern, sourceKind, path, file, lineStart, symbol)",
        },
        "estimationGuidance": {
            "purpose": (
                "Use this sheet for route-record operation-vs-domain cancellation precision. "
                "Do not use it to update unique-family denominator claims."
            ),
            "primaryEstimate": (
                "Compute stratum rates and a route-record weighted estimate using "
                "routeFramePopulationRecords. Route strata are exclusive for this sheet."
            ),
            "blindLabeling": (
                "Hide routeStratum and automated linkage columns from human labelers; "
                "use them only for sampling weights and post-label analysis."
            ),
            "deleteOperationResource": (
                "Sampled at higher density because it determines the operation-resource "
                "linked envelope around the cancellation candidate."
            ),
        },
    }


def cell_route_sample_summary(rows: list[dict[str, str]], *, seed: int, paths: DataPaths) -> dict[str, Any]:
    by_pattern = Counter(row["pattern"] for row in rows)
    by_cell = Counter(row["cell_sample_id"] for row in rows)
    by_source_kind = Counter(row["sourceKind"] for row in rows)
    cell_sizes = list(by_cell.values())
    return {
        "samplingUnit": "family-pattern-cell-route",
        "estimationPopulation": "sampled-family-pattern-cell-routes",
        "sampleCount": len(rows),
        "sampledCells": len(by_cell),
        "byPattern": dict(sorted(by_pattern.items())),
        "bySourceKind": dict(sorted(by_source_kind.items())),
        "cellRouteCounts": {
            "distribution": {
                str(count): frequency
                for count, frequency in sorted(Counter(cell_sizes).items())
            },
            "selectedCells": len(cell_sizes),
            "selectedRouteRecords": sum(cell_sizes),
            "extraRouteLabelsOverRepresentatives": sum(cell_sizes) - len(cell_sizes),
        },
        "selectionProvenance": {
            **sampling_provenance(paths=paths, seed=seed),
            "seed": seed,
            "cellSelection": (
                "Uses the same sampled family_id x pattern cells as the pattern-family "
                "representative sheet, then includes every cancellation route record in each selected cell."
            ),
            "routeId": "sha256(repository, httpMethod, normalizedPath-or-path)",
            "evidenceId": "sha256(route_id, commit, pattern, sourceKind, path, file, lineStart, symbol)",
        },
        "estimationGuidance": {
            "purpose": (
                "Use this companion sheet when manual labeling needs to observe within-cell "
                "operation/domain mixing. Aggregate route labels back to cell_sample_id before "
                "estimating pattern-family membership precision."
            ),
            "doNotUseAsRouteFrame": True,
            "blinding": (
                "Create a separate reviewer view that hides automated linkage columns before labeling."
            ),
        },
    }


def sampling_provenance(*, paths: DataPaths, seed: int) -> dict[str, str | int]:
    return {
        "seed": seed,
        "samplingCodeCommit": sampling_code_commit(),
        "pythonVersion": sys.version.split()[0],
        "frameSnapshotHash": frame_snapshot_hash(paths),
    }


def sampling_code_commit() -> str:
    override = os.environ.get("RFC_MINER_SAMPLING_CODE_COMMIT")
    if override:
        return override
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def frame_snapshot_hash(paths: DataPaths) -> str:
    digest = hashlib.sha256()
    for source in (paths.normalized_evidence, paths.families):
        digest.update(source.name.encode("utf-8"))
        digest.update(b"\0")
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, str]], *, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
            lineterminator="\n",
        )
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


def format_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return ""
    return f"{numerator / denominator:.6f}"


def format_float(value: float) -> str:
    return f"{value:.6f}"
