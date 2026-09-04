from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
    data_dir: Path
    raw_dir: Path
    normalized_dir: Path
    results_dir: Path
    candidates_dir: Path
    repositories: Path
    raw_evidence: Path
    errors: Path
    normalized_evidence: Path
    families: Path
    clusters: Path
    standards_comparison: Path
    opportunity_scores: Path
    report: Path
    manual_review: Path


def data_paths(data_dir: str | Path) -> DataPaths:
    root = Path(data_dir)
    raw = root / "raw"
    normalized = root / "normalized"
    results = root / "results"
    candidates = results / "candidates"
    return DataPaths(
        data_dir=root,
        raw_dir=raw,
        normalized_dir=normalized,
        results_dir=results,
        candidates_dir=candidates,
        repositories=raw / "repositories.jsonl",
        raw_evidence=raw / "evidence.jsonl",
        errors=raw / "errors.jsonl",
        normalized_evidence=normalized / "evidence.jsonl",
        families=normalized / "families.jsonl",
        clusters=results / "clusters.json",
        standards_comparison=results / "standards-comparison.json",
        opportunity_scores=results / "opportunity-scores.json",
        report=results / "report.md",
        manual_review=results / "manual-review.md",
    )


def ensure_data_dirs(paths: DataPaths) -> None:
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    paths.normalized_dir.mkdir(parents=True, exist_ok=True)
    paths.results_dir.mkdir(parents=True, exist_ok=True)
    paths.candidates_dir.mkdir(parents=True, exist_ok=True)
