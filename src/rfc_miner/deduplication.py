from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from .io import read_jsonl, write_jsonl
from .paths import DataPaths, ensure_data_dirs


def dedupe_repositories(
    *,
    paths: DataPaths,
    repositories_path: str | Path | None = None,
    normalized_evidence_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_data_dirs(paths)
    repositories = read_jsonl(repositories_path or paths.repositories)
    evidence = read_jsonl(normalized_evidence_path or paths.normalized_evidence)
    signatures = api_signatures(evidence)
    duplicate_signatures = {
        signature
        for signature, repos in signatures.items()
        if signature and len(repos) > 1
    }

    records: list[dict[str, Any]] = []
    for repo in repositories:
        repo_id = str(repo.get("repo_id") or "")
        signature = signature_for_repo(evidence, repo_id)
        excluded, exclusion_reason = exclusion(repo)
        family_id = repo_id
        confidence = "unknown"
        basis = "single-repository"

        if repo.get("fork_parent"):
            family_id = f"github:{repo['fork_parent']}"
            confidence = "exact"
            basis = "github-fork-parent"
        elif repo.get("probable_origin"):
            family_id = f"origin:{repo['probable_origin']}"
            confidence = "probable"
            basis = "probable-origin"
        elif signature in duplicate_signatures:
            family_id = f"api-signature:{signature}"
            confidence = "probable"
            basis = "shared-normalized-api-signature"

        records.append(
            {
                "repo_id": repo_id,
                "family_id": family_id,
                "confidence": confidence,
                "basis": basis,
                "api_signature": signature,
                "excluded_from_independent_count": excluded,
                "exclusion_reason": exclusion_reason,
            }
        )

    write_jsonl(paths.families, records)
    return records


def api_signatures(evidence: list[dict[str, Any]]) -> dict[str, set[str]]:
    by_repo: dict[str, list[str]] = defaultdict(list)
    for record in evidence:
        repo = str(record.get("repository") or "")
        by_repo[repo].append(
            "|".join(
                [
                    str(record.get("concept") or ""),
                    str(record.get("pattern") or ""),
                    str(record.get("httpMethod") or ""),
                    str(record.get("normalizedPath") or ""),
                ]
            )
        )

    signatures: dict[str, set[str]] = defaultdict(set)
    for repo, values in by_repo.items():
        signature = hash_values(values)
        signatures[signature].add(repo)
    return signatures


def signature_for_repo(evidence: list[dict[str, Any]], repo_id: str) -> str:
    values = [
        "|".join(
            [
                str(record.get("concept") or ""),
                str(record.get("pattern") or ""),
                str(record.get("httpMethod") or ""),
                str(record.get("normalizedPath") or ""),
            ]
        )
        for record in evidence
        if record.get("repository") == repo_id
    ]
    return hash_values(values)


def hash_values(values: list[str]) -> str:
    if not values:
        return ""
    payload = "\n".join(sorted(set(values))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def exclusion(repo: dict[str, Any]) -> tuple[bool, str | None]:
    category = str(repo.get("project_category") or "").lower()
    template = str(repo.get("probable_template") or "").lower()
    name = str(repo.get("name") or "").lower()
    if "generated-sdk" in category or "generated-sdk" in template:
        return True, "generated-sdk"
    if category in {"tutorial", "toy", "demo", "sample"}:
        return True, category
    if template == "name-indicator" and any(word in name for word in ["demo", "sample", "starter"]):
        return True, "template-or-demo"
    return False, None
