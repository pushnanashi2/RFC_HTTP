from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EXTRACTOR_VERSION = "0.1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repository_record(
    *,
    repository_url: str,
    owner: str,
    name: str,
    language: str | None = None,
    framework: str | None = None,
    stars: int | None = None,
    forks: int | None = None,
    license_name: str | None = None,
    last_activity: str | None = None,
    default_branch: str | None = None,
    commit_hash: str | None = None,
    project_category: str | None = None,
    fork_parent: str | None = None,
    probable_template: str | None = None,
    probable_origin: str | None = None,
    vendor: str | None = None,
    local_path: str | None = None,
) -> dict[str, Any]:
    return {
        "repo_id": f"{owner}/{name}",
        "repository_url": repository_url,
        "owner": owner,
        "name": name,
        "language": language,
        "framework": framework,
        "stars": stars,
        "forks": forks,
        "license": license_name,
        "last_activity": last_activity,
        "default_branch": default_branch,
        "commit_hash": commit_hash,
        "project_category": project_category,
        "fork_parent": fork_parent,
        "probable_template": probable_template,
        "probable_origin": probable_origin,
        "vendor": vendor or owner,
        "collection_timestamp": utc_now(),
        "local_path": local_path,
    }


def evidence_record(
    *,
    repository: str,
    commit: str | None,
    concept: str,
    evidence_type: str,
    http_method: str,
    path: str,
    response_codes: list[int] | None,
    file: str,
    line_start: int,
    line_end: int | None = None,
    symbol: str | None = None,
    confidence: float = 0.5,
    extracted_value: dict[str, Any] | None = None,
    extractor: str,
) -> dict[str, Any]:
    return {
        "repository": repository,
        "commit": commit,
        "concept": concept,
        "evidenceType": evidence_type,
        "httpMethod": http_method.upper(),
        "path": path,
        "responseCodes": sorted(set(response_codes or [])),
        "file": file,
        "symbol": symbol,
        "lineStart": line_start,
        "lineEnd": line_end or line_start,
        "confidence": round(float(confidence), 4),
        "extractedValue": extracted_value or {},
        "extractor": extractor,
        "extractorVersion": EXTRACTOR_VERSION,
    }


def error_record(
    *,
    repo: str,
    stage: str,
    error_type: str,
    error: str,
    retryable: bool,
) -> dict[str, Any]:
    return {
        "repo": repo,
        "stage": stage,
        "errorType": error_type,
        "error": error,
        "retryable": retryable,
        "timestamp": utc_now(),
    }
