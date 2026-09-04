from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, read_jsonl
from .paths import DataPaths, ensure_data_dirs


def write_report(*, paths: DataPaths) -> str:
    ensure_data_dirs(paths)
    clusters = read_json(paths.clusters, default={"concepts": {}})
    scores = read_json(paths.opportunity_scores, default={"scores": []})
    standards = read_json(paths.standards_comparison, default={"concepts": {}})
    errors = read_jsonl(paths.errors)
    raw_evidence = read_jsonl(paths.raw_evidence)
    evidence = read_jsonl(paths.normalized_evidence)

    lines: list[str] = []
    lines.append("# RFC HTTP Miner Report")
    lines.append("")
    lines.append("## Corpus")
    lines.append("")
    lines.append(f"- Raw repositories: {clusters.get('rawRepositoryCount', 0)}")
    lines.append(f"- Independent implementation families: {clusters.get('independentFamilyCount', 0)}")
    lines.append(f"- Raw evidence records: {len(raw_evidence)}")
    lines.append(f"- Deduplicated evidence records: {len(evidence)}")
    lines.append(f"- Extraction errors: {len(errors)}")
    lines.append("")
    lines.append("## Top Standardization Opportunities")
    lines.append("")
    lines.append("| Rank | Concept | Score | Strict score | Families | Strict families | Patterns | Standards coverage |")
    lines.append("| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for index, score in enumerate(scores.get("scores") or [], start=1):
        lines.append(
            "| {rank} | `{concept}` | {score} | {strict_score} | {families} | {strict_families} | {patterns} | {coverage} |".format(
                rank=index,
                concept=score["concept"],
                score=score["score"],
                strict_score=score.get("strictScore", 0),
                families=score.get("independentFamilyCount", 0),
                strict_families=score.get("strictIndependentFamilyCount", 0),
                patterns=score.get("patternCount", 0),
                coverage=score.get("bestStandardsCoverage", "unknown"),
            )
        )
    lines.append("")

    for score in scores.get("scores") or []:
        concept = score["concept"]
        detail = candidate_detail(concept, clusters, standards, score)
        candidate_path = paths.candidates_dir / f"{concept}.md"
        candidate_path.write_text(detail, encoding="utf-8")
        lines.append(f"- Candidate detail: `{candidate_path.as_posix()}`")

    if errors:
        lines.append("")
        lines.append("## Extraction Errors")
        lines.append("")
        for error in errors[:20]:
            lines.append(
                f"- `{error.get('repo')}` `{error.get('stage')}` `{error.get('errorType')}`: {error.get('error')}"
            )
        if len(errors) > 20:
            lines.append(f"- ... {len(errors) - 20} more")

    content = "\n".join(lines) + "\n"
    paths.report.write_text(content, encoding="utf-8")
    write_manual_review(paths=paths, evidence=evidence, errors=errors)
    return content


def write_manual_review(
    *,
    paths: DataPaths,
    evidence: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Manual Validation Review",
        "",
        "Use this file to sample extractor quality before expanding the corpus.",
        "",
        "Legend:",
        "",
        "- TP: true positive",
        "- FP: false positive",
        "- FN candidate: likely missed route or concept",
        "- Unclassified: evidence exists but pattern rules need refinement",
        "",
        "## Evidence Samples",
        "",
    ]
    for record in sorted(evidence, key=lambda item: (item.get("concept", ""), item.get("repository", ""), item.get("file", ""), item.get("lineStart", 0)))[:100]:
        lines.append(
            "- [ ] TP  [ ] FP  [ ] Unclassified — "
            "`{concept}` `{pattern}` `{repo}` `{method} {path}` `{file}:{line}` confidence={confidence}".format(
                concept=record.get("concept"),
                pattern=record.get("pattern"),
                repo=record.get("repository"),
                method=record.get("httpMethod"),
                path=record.get("path"),
                file=record.get("file"),
                line=record.get("lineStart"),
                confidence=record.get("confidence"),
            )
        )
    lines.append("")
    lines.append("## False Negative Candidates")
    lines.append("")
    lines.append("- [ ] Add routes or files that manual inspection shows were missed.")
    lines.append("")
    lines.append("## Repository Errors")
    lines.append("")
    if errors:
        for error in errors[:100]:
            lines.append(
                "- [ ] Review — `{repo}` `{stage}` `{error_type}` retryable={retryable}: {message}".format(
                    repo=error.get("repo"),
                    stage=error.get("stage"),
                    error_type=error.get("errorType"),
                    retryable=error.get("retryable"),
                    message=error.get("error"),
                )
            )
    else:
        lines.append("- No repository errors recorded.")
    paths.manual_review.write_text("\n".join(lines) + "\n", encoding="utf-8")


def candidate_detail(
    concept: str,
    clusters: dict[str, Any],
    standards: dict[str, Any],
    score: dict[str, Any],
) -> str:
    metrics = (clusters.get("concepts") or {}).get(concept, {})
    comparison = (standards.get("concepts") or {}).get(concept, {})
    lines: list[str] = [f"# Candidate: {concept}", ""]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Score: {score.get('score', 0)}")
    lines.append(f"- Strict score: {score.get('strictScore', 0)}")
    lines.append(f"- Independent families: {metrics.get('independentFamilyCount', 0)}")
    lines.append(f"- Strict independent families: {score.get('strictIndependentFamilyCount', 0)}")
    lines.append(f"- Raw repositories: {metrics.get('repositoryCount', 0)}")
    lines.append(f"- Strict repositories: {score.get('strictRepositoryCount', 0)}")
    lines.append(f"- Deduplicated evidence records: {metrics.get('evidenceCount', 0)}")
    lines.append(f"- Strict evidence records: {score.get('strictEvidenceCount', 0)}")
    lines.append(f"- Capped evidence records: {metrics.get('cappedEvidenceCount', 0)}")
    lines.append(f"- Dominant repository evidence share: {metrics.get('dominantRepositoryEvidenceRatio', 0)}")
    lines.append(f"- Observed patterns: {metrics.get('numberOfPatterns', 0)}")
    lines.append(f"- Strict patterns: {score.get('strictPatternCount', 0)}")
    lines.append(f"- Best seeded standards coverage: {comparison.get('bestCoverage', 'unknown')}")
    lines.append("")
    lines.append("## Evidence Concentration")
    lines.append("")
    for entry in metrics.get("topEvidenceRepositories") or []:
        lines.append(
            "- `{repository}`: {count} records, share={share}".format(
                repository=entry.get("repository"),
                count=entry.get("evidenceCount"),
                share=entry.get("share"),
            )
        )
    lines.append("")
    lines.append("## Strict Evidence")
    lines.append("")
    lines.append("Strict mode counts only the strongest interaction patterns for this concept:")
    for pattern in score.get("strictPatterns") or []:
        lines.append(f"- `{pattern}`")
    lines.append("")
    lines.append("## Observed Practice")
    lines.append("")
    for pattern, pattern_metrics in sorted((metrics.get("patterns") or {}).items()):
        lines.append(
            f"- `{pattern}`: {pattern_metrics.get('familyCount', 0)} families, "
            f"{pattern_metrics.get('repositoryCount', 0)} repositories"
        )
        for example in pattern_metrics.get("examples", [])[:3]:
            lines.append(
                "  - `{repo}` `{method} {path}` `{file}:{line}` confidence={confidence}".format(
                    repo=example.get("repository"),
                    method=example.get("httpMethod"),
                    path=example.get("path"),
                    file=example.get("file"),
                    line=example.get("lineStart"),
                    confidence=example.get("confidence"),
                )
            )
    lines.append("")
    lines.append("## Standards Gap")
    lines.append("")
    for entry in comparison.get("comparisons") or []:
        lines.append(
            f"- `{entry.get('existingStandard')}` {entry.get('coverage')}: {entry.get('gap')}"
        )
    lines.append("")
    lines.append("## Why High")
    lines.append("")
    for reason in score.get("whyHigh") or []:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Why Low")
    lines.append("")
    for reason in score.get("whyLow") or []:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Counterarguments")
    lines.append("")
    for argument in score.get("counterarguments") or []:
        lines.append(f"- {argument}")
    lines.append("")
    lines.append("## Candidate Specification Scope")
    lines.append("")
    lines.append("- Define only reusable HTTP interaction semantics observed across independent implementations.")
    lines.append("- Avoid standardizing implementation bugs or framework-specific conventions.")
    return "\n".join(lines) + "\n"
