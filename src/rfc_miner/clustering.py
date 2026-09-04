from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .io import read_jsonl, write_json
from .paths import DataPaths, ensure_data_dirs


MAX_EVIDENCE_PER_REPOSITORY_CONCEPT = 50


def cluster_patterns(
    *,
    paths: DataPaths,
    repositories_path: str | Path | None = None,
    normalized_evidence_path: str | Path | None = None,
    families_path: str | Path | None = None,
) -> dict[str, Any]:
    ensure_data_dirs(paths)
    repositories = read_jsonl(repositories_path or paths.repositories)
    evidence = read_jsonl(normalized_evidence_path or paths.normalized_evidence)
    families = read_jsonl(families_path or paths.families)
    repo_by_id = {repo["repo_id"]: repo for repo in repositories if "repo_id" in repo}
    family_by_repo = {record["repo_id"]: record for record in families if "repo_id" in record}

    included_family_ids = {
        record["family_id"]
        for record in families
        if record.get("family_id") and not record.get("excluded_from_independent_count")
    }

    clusters: dict[str, Any] = {
        "rawRepositoryCount": len(repositories),
        "independentFamilyCount": len(included_family_ids),
        "concepts": {},
    }

    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in evidence:
        repo_id = str(record.get("repository") or "")
        family = family_by_repo.get(repo_id)
        if family and family.get("excluded_from_independent_count"):
            continue
        by_concept[str(record.get("concept") or "unknown")].append(record)

    for concept, records in sorted(by_concept.items()):
        repo_ids = {str(record.get("repository")) for record in records}
        family_ids = {
            str(family_by_repo.get(str(record.get("repository")), {}).get("family_id") or record.get("repository"))
            for record in records
        }
        pattern_families: dict[str, set[str]] = defaultdict(set)
        pattern_repos: dict[str, set[str]] = defaultdict(set)
        pattern_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
        repository_evidence_counts = Counter(str(record.get("repository") or "unknown") for record in records)

        for record in records:
            pattern = str(record.get("pattern") or "unknown")
            repo_id = str(record.get("repository") or "")
            family_id = str(family_by_repo.get(repo_id, {}).get("family_id") or repo_id)
            pattern_families[pattern].add(family_id)
            pattern_repos[pattern].add(repo_id)
            if len(pattern_examples[pattern]) < 5:
                pattern_examples[pattern].append(example(record))

        pattern_counts = {pattern: len(ids) for pattern, ids in pattern_families.items()}
        total_pattern_families = sum(pattern_counts.values())
        entropy = normalized_entropy(pattern_counts)
        dominant_ratio = (max(pattern_counts.values()) / total_pattern_families) if total_pattern_families else 0.0
        long_tail_ratio = (
            sum(1 for count in pattern_counts.values() if count == 1) / len(pattern_counts)
            if pattern_counts
            else 0.0
        )

        concept_repos = [repo_by_id[repo_id] for repo_id in repo_ids if repo_id in repo_by_id]
        clusters["concepts"][concept] = {
            "repositoryCount": len(repo_ids),
            "independentFamilyCount": len(family_ids),
            "evidenceCount": len(records),
            "cappedEvidenceCount": sum(
                min(count, MAX_EVIDENCE_PER_REPOSITORY_CONCEPT)
                for count in repository_evidence_counts.values()
            ),
            "dominantRepositoryEvidenceRatio": round(
                max(repository_evidence_counts.values()) / len(records),
                4,
            ) if records else 0.0,
            "topEvidenceRepositories": [
                {
                    "repository": repository,
                    "evidenceCount": count,
                    "share": round(count / len(records), 4) if records else 0.0,
                }
                for repository, count in repository_evidence_counts.most_common(10)
            ],
            "numberOfPatterns": len(pattern_counts),
            "entropy": round(entropy, 4),
            "dominantPatternRatio": round(dominant_ratio, 4),
            "longTailRatio": round(long_tail_ratio, 4),
            "languageDistribution": count_field(concept_repos, "language"),
            "frameworkDistribution": count_field(concept_repos, "framework"),
            "vendorDistribution": count_field(concept_repos, "vendor"),
            "patterns": {
                pattern: {
                    "familyCount": len(pattern_families[pattern]),
                    "repositoryCount": len(pattern_repos[pattern]),
                    "examples": pattern_examples[pattern],
                }
                for pattern in sorted(pattern_counts)
            },
        }

    write_json(paths.clusters, clusters)
    return clusters


def normalized_entropy(counts: dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log(probability)
    return entropy / math.log(len(counts))


def count_field(repositories: list[dict[str, Any]], field: str) -> dict[str, int]:
    counter = Counter(str(repo.get(field) or "unknown") for repo in repositories)
    return dict(sorted(counter.items()))


def example(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": record.get("repository"),
        "commit": record.get("commit"),
        "file": record.get("file"),
        "lineStart": record.get("lineStart"),
        "httpMethod": record.get("httpMethod"),
        "path": record.get("path"),
        "normalizedPath": record.get("normalizedPath"),
        "confidence": record.get("confidence"),
        "extractor": record.get("extractor"),
    }
