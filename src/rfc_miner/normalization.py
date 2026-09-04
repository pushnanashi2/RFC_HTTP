from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .http_semantics import has_async_noun, has_cancel_word, has_status_word
from .io import read_jsonl, write_jsonl
from .paths import DataPaths, ensure_data_dirs


def normalize_evidence(
    *,
    paths: DataPaths,
    raw_evidence_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    ensure_data_dirs(paths)
    records = read_jsonl(raw_evidence_path or paths.raw_evidence)
    normalized = deduplicate_normalized_records([normalize_record(record) for record in records])
    write_jsonl(paths.normalized_evidence, normalized)
    return normalized


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized_path = normalize_path(str(record.get("path") or ""))
    pattern, pattern_reason = assign_pattern(record, normalized_path)
    enriched = dict(record)
    enriched["normalizedPath"] = normalized_path
    enriched["pattern"] = pattern
    enriched["patternReason"] = pattern_reason
    enriched["sourceKind"] = source_kind(record)
    enriched["normalizationRules"] = ["http-path-template-v1", f"{record.get('concept')}-pattern-v1"]
    return enriched


def deduplicate_normalized_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    duplicate_counts: dict[tuple[str, str, str, str, str], int] = {}

    for record in records:
        key = deduplication_key(record)
        current = buckets.get(key)
        if current is None:
            buckets[key] = dict(record)
            duplicate_counts[key] = 1
            continue

        merged_codes = sorted(set(response_codes(current)) | set(response_codes(record)))
        winner = dict(record if evidence_quality_key(record) > evidence_quality_key(current) else current)
        winner["responseCodes"] = merged_codes
        buckets[key] = winner
        duplicate_counts[key] += 1

    deduplicated: list[dict[str, Any]] = []
    for key, record in buckets.items():
        normalized_path = str(record.get("normalizedPath") or normalize_path(str(record.get("path") or "")))
        pattern, pattern_reason = assign_pattern(record, normalized_path)
        record["normalizedPath"] = normalized_path
        record["pattern"] = pattern
        record["patternReason"] = pattern_reason
        if duplicate_counts[key] > 1:
            record["duplicateEvidenceCount"] = duplicate_counts[key]
        else:
            record.pop("duplicateEvidenceCount", None)
        deduplicated.append(record)
    return deduplicated


def deduplication_key(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(record.get("repository") or ""),
        str(record.get("concept") or ""),
        str(record.get("httpMethod") or "").upper(),
        str(record.get("normalizedPath") or ""),
        str(record.get("sourceKind") or source_kind(record)),
    )


def evidence_quality_key(record: dict[str, Any]) -> tuple[int, int, float, int, int]:
    codes = set(response_codes(record))
    line = safe_int(record.get("lineStart"), default=1_000_000)
    return (
        1 if 202 in codes else 0,
        len(codes),
        safe_float(record.get("confidence"), default=0.0),
        1 if record.get("symbol") else 0,
        -line,
    )


def response_codes(record: dict[str, Any]) -> list[int]:
    codes: list[int] = []
    for code in record.get("responseCodes") or []:
        try:
            codes.append(int(code))
        except (TypeError, ValueError):
            continue
    return sorted(set(codes))


def source_kind(record: dict[str, Any]) -> str:
    extractor = str(record.get("extractor") or "unknown").lower()
    if extractor.startswith("openapi"):
        return "openapi"
    if extractor == "source-routes":
        return "source"
    return extractor


def safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_path(path: str) -> str:
    path = path.split("?", 1)[0].strip()
    if not path:
        return "/"
    path = re.sub(r"<(?:[^:<>]+:)?[^<>]+>", "{var}", path)
    path = re.sub(r"\{[^}/]+\}", "{var}", path)
    path = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", "{var}", path)
    path = re.sub(r"\([^/]+\)", "{var}", path)
    path = re.sub(r"//+", "/", path)
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def assign_pattern(record: dict[str, Any], normalized_path: str) -> tuple[str, str]:
    concept = record.get("concept")
    method = str(record.get("httpMethod") or "").upper()
    response_codes = set(record.get("responseCodes") or [])
    combined_text = " ".join(
        [
            normalized_path,
            str(record.get("path") or ""),
            str(record.get("symbol") or ""),
            extracted_value_text(record.get("extractedValue")),
        ]
    )
    path_text = " ".join([normalized_path, str(record.get("path") or "")])

    if concept == "http-cancellation":
        if method == "POST" and re.search(r"/(?:cancel|abort|stop|terminate|kill)$", normalized_path.lower()):
            return "post-subresource-cancel", "POST action subresource ending in a cancellation verb"
        if method == "PUT" and has_cancel_word(combined_text):
            return "put-action-cancel", "PUT route path or operation name contains cancellation action wording"
        if method == "GET" and has_cancel_word(path_text):
            return "get-cancel-link", "GET cancellation link or signed action URL"
        if method == "POST" and has_cancel_word(combined_text):
            return "post-action-cancel", "POST route associated with cancellation wording"
        if method == "DELETE" and has_cancel_word(combined_text):
            return "delete-action-cancel", "DELETE route path or operation name contains cancellation action wording"
        if method == "DELETE" and has_async_noun(combined_text):
            return "delete-operation-resource", "DELETE applied to job/operation-like resource"
        if method == "PATCH" and has_cancel_word(combined_text):
            return "patch-state-cancelled", "PATCH route associated with cancellation wording"
        return "other-cancellation-route", "cancellation concept without a known interaction pattern"

    if concept == "http-async-operation":
        if method == "POST" and 202 in response_codes:
            return "post-202-accepted", "POST returns 202 Accepted"
        if method == "POST" and has_async_noun(combined_text):
            return "post-job-resource", "POST creates job/operation-like resource"
        if method == "GET" and has_status_word(combined_text):
            return "get-status-resource", "GET exposes status/progress-like resource"
        if method == "GET" and has_async_noun(combined_text):
            return "get-operation-resource", "GET exposes job/operation-like resource"
        if method in {"PUT", "PATCH", "DELETE"} and 202 in response_codes:
            return "mutation-202-accepted", f"{method} returns 202 Accepted"
        return "other-async-route", "async concept without a known interaction pattern"

    return "unclassified", "unknown concept"


def extracted_value_text(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value or "")

    fragments: list[str] = []
    for key in ("operationId", "summary", "description"):
        item = value.get(key)
        if isinstance(item, str):
            fragments.append(item)
    tags = value.get("tags")
    if isinstance(tags, list):
        fragments.extend(str(tag) for tag in tags)
    return " ".join(fragments)
