from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .paths import DataPaths, ensure_data_dirs


COVERAGE_ORDER = {
    "unknown": 0,
    "none": 1,
    "adjacent": 2,
    "partial": 3,
    "full": 4,
}


def compare_standards(
    *,
    paths: DataPaths,
    standards_path: str | Path,
) -> dict[str, Any]:
    ensure_data_dirs(paths)
    clusters = read_json(paths.clusters, default={"concepts": {}})
    standards = read_json(standards_path, default={"standards": []})
    standards_list = standards.get("standards", []) if isinstance(standards, dict) else []

    comparisons: dict[str, Any] = {
        "methodology": "seeded-deterministic-standards-map",
        "concepts": {},
    }
    for concept in sorted((clusters.get("concepts") or {}).keys()):
        entries = [
            summarize_standard(standard, concept)
            for standard in standards_list
            if concept in standard.get("concepts", [])
        ]
        if not entries:
            entries = [
                {
                    "concept": concept,
                    "existingStandard": None,
                    "coverage": "unknown",
                    "gap": "No seeded standards comparison exists for this concept.",
                    "conflict": "unknown",
                    "evidence": [],
                    "confidence": 0.0,
                }
            ]
        comparisons["concepts"][concept] = {
            "bestCoverage": best_coverage(entries),
            "comparisons": entries,
        }

    write_json(paths.standards_comparison, comparisons)
    return comparisons


def summarize_standard(standard: dict[str, Any], concept: str) -> dict[str, Any]:
    concept_entry = (standard.get("conceptCoverage") or {}).get(concept, {})
    coverage = concept_entry.get("coverage") or standard.get("defaultCoverage") or "unknown"
    return {
        "concept": concept,
        "existingStandard": standard.get("id"),
        "title": standard.get("title"),
        "url": standard.get("url"),
        "coverage": coverage,
        "gap": concept_entry.get("gap") or standard.get("gap") or "",
        "conflict": concept_entry.get("conflict") or "none",
        "evidence": concept_entry.get("evidence") or [],
        "confidence": concept_entry.get("confidence", standard.get("confidence", 0.7)),
    }


def best_coverage(entries: list[dict[str, Any]]) -> str:
    return max(
        (str(entry.get("coverage") or "unknown") for entry in entries),
        key=lambda coverage: COVERAGE_ORDER.get(coverage, 0),
        default="unknown",
    )
