from __future__ import annotations

from pathlib import Path
from typing import Any

from .extractors.openapi import extract_openapi
from .extractors.source_routes import extract_source_routes
from .io import read_jsonl, write_jsonl
from .models import error_record
from .paths import DataPaths, ensure_data_dirs


EXTRACTORS = [extract_openapi, extract_source_routes]


def analyze_repositories(
    *,
    paths: DataPaths,
    repositories_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ensure_data_dirs(paths)
    repo_records = read_jsonl(repositories_path or paths.repositories)
    if repositories_path:
        write_jsonl(paths.repositories, repo_records)
    evidence: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for repo in repo_records:
        repo_id = str(repo.get("repo_id") or "")
        local_path = repo.get("local_path")
        if not local_path:
            errors.append(
                error_record(
                    repo=repo_id,
                    stage="analyze",
                    error_type="missing_local_path",
                    error="repository record has no local_path",
                    retryable=False,
                )
            )
            continue
        root = Path(str(local_path))
        if not root.exists():
            errors.append(
                error_record(
                    repo=repo_id,
                    stage="analyze",
                    error_type="missing_checkout",
                    error=f"local_path does not exist: {root}",
                    retryable=True,
                )
            )
            continue

        for extractor in EXTRACTORS:
            try:
                evidence.extend(extractor(repo, root))
            except Exception as error:  # noqa: BLE001 - corpus runs must isolate repo failures
                errors.append(
                    error_record(
                        repo=repo_id,
                        stage="analyze",
                        error_type=error.__class__.__name__,
                        error=str(error),
                        retryable=False,
                    )
                )

    write_jsonl(paths.raw_evidence, evidence)
    write_jsonl(paths.errors, errors)
    return evidence, errors
