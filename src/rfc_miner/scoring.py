from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .paths import DataPaths, ensure_data_dirs
from .standards import COVERAGE_ORDER


INTEROPERABILITY_VALUE = {
    "http-async-operation": 13,
    "http-cancellation": 12,
}

SPEC_TRACTABILITY = {
    "http-async-operation": 4,
    "http-cancellation": 5,
}


def score_opportunities(
    *,
    paths: DataPaths,
    clusters_path: str | Path | None = None,
    standards_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_data_dirs(paths)
    clusters = read_json(clusters_path or paths.clusters, default={"concepts": {}})
    standards = read_json(standards_path or paths.standards_comparison, default={"concepts": {}})
    total_families = int(clusters.get("independentFamilyCount") or 0)
    scores: list[dict[str, Any]] = []

    for concept, metrics in sorted((clusters.get("concepts") or {}).items()):
        family_count = int(metrics.get("independentFamilyCount") or 0)
        pattern_count = int(metrics.get("numberOfPatterns") or 0)
        entropy = float(metrics.get("entropy") or 0.0)
        best_coverage = (
            (standards.get("concepts") or {}).get(concept, {}).get("bestCoverage")
            or "unknown"
        )
        conflicts = standards_conflicts((standards.get("concepts") or {}).get(concept, {}))
        components = {
            "prevalence": prevalence_score(family_count, total_families),
            "independentImplementations": independent_score(family_count),
            "implementationDivergence": round(entropy * 20),
            "interoperabilityValue": INTEROPERABILITY_VALUE.get(concept, 10),
            "standardsGap": standards_gap_score(best_coverage),
            "standardsCorrectness": 2 if conflicts else 4,
            "specificationTractability": SPEC_TRACTABILITY.get(concept, 3),
        }
        total = int(sum(components.values()))
        scores.append(
            {
                "concept": concept,
                "score": total,
                "components": components,
                "rawRepositoryCount": metrics.get("repositoryCount", 0),
                "independentFamilyCount": family_count,
                "patternCount": pattern_count,
                "bestStandardsCoverage": best_coverage,
                "whyHigh": why_high(concept, metrics, best_coverage),
                "whyLow": why_low(metrics, best_coverage, conflicts),
                "counterarguments": counterarguments(concept, metrics, best_coverage),
            }
        )

    scores.sort(key=lambda record: record["score"], reverse=True)
    result = {
        "rawRepositoryCount": clusters.get("rawRepositoryCount", 0),
        "independentFamilyCount": total_families,
        "scores": scores,
    }
    write_json(paths.opportunity_scores, result)
    return result


def prevalence_score(family_count: int, total_families: int) -> int:
    if total_families <= 0:
        return 0
    return round(min(1.0, family_count / total_families) * 20)


def independent_score(family_count: int) -> int:
    return round(min(1.0, family_count / 20) * 20)


def standards_gap_score(best_coverage: str) -> int:
    rank = COVERAGE_ORDER.get(best_coverage, 0)
    if rank >= COVERAGE_ORDER["full"]:
        return 1
    if rank == COVERAGE_ORDER["partial"]:
        return 8
    if rank == COVERAGE_ORDER["adjacent"]:
        return 12
    if rank == COVERAGE_ORDER["none"]:
        return 15
    return 10


def standards_conflicts(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for entry in comparison.get("comparisons") or []:
        if entry.get("conflict") not in {None, "", "none", "unknown"}:
            conflicts.append(entry)
    return conflicts


def why_high(concept: str, metrics: dict[str, Any], best_coverage: str) -> list[str]:
    reasons: list[str] = []
    if metrics.get("independentFamilyCount", 0) >= 5:
        reasons.append("Observed across multiple independent implementation families.")
    if metrics.get("numberOfPatterns", 0) >= 3:
        reasons.append("Multiple interaction patterns indicate real implementation divergence.")
    if best_coverage in {"none", "adjacent", "unknown"}:
        reasons.append("Existing seeded standards do not fully cover the observed concept.")
    if concept == "http-cancellation":
        reasons.append("Cancellation affects client interoperability and safe operation lifecycle handling.")
    if concept == "http-async-operation":
        reasons.append("Asynchronous operations shape polling, progress, result, and retry behavior.")
    return reasons or ["Score is driven by the current corpus metrics."]


def why_low(metrics: dict[str, Any], best_coverage: str, conflicts: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if metrics.get("independentFamilyCount", 0) < 5:
        reasons.append("Stage corpus has limited independent-family evidence.")
    if metrics.get("numberOfPatterns", 0) <= 1:
        reasons.append("Low observed divergence may not justify a new standard.")
    if best_coverage in {"full", "partial"}:
        reasons.append("Seeded standards already cover part of the concept.")
    if conflicts:
        reasons.append("Some observed practice may conflict with existing standards.")
    return reasons


def counterarguments(concept: str, metrics: dict[str, Any], best_coverage: str) -> list[str]:
    arguments = [
        "Stage-1 extraction may undercount dynamic framework routes.",
        "OpenAPI-documented APIs may not represent internal server practice.",
    ]
    if best_coverage == "partial":
        arguments.append("An implementation guide or profile may be more appropriate than a new RFC.")
    if metrics.get("vendorDistribution") and len(metrics["vendorDistribution"]) <= 2:
        arguments.append("Vendor concentration may inflate apparent prevalence.")
    if concept == "http-cancellation":
        arguments.append("Cancellation semantics may depend on domain-specific safety guarantees.")
    return arguments
