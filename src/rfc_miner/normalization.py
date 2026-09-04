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
    normalized = [normalize_record(record) for record in records]
    write_jsonl(paths.normalized_evidence, normalized)
    return normalized


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized_path = normalize_path(str(record.get("path") or ""))
    pattern, pattern_reason = assign_pattern(record, normalized_path)
    enriched = dict(record)
    enriched["normalizedPath"] = normalized_path
    enriched["pattern"] = pattern
    enriched["patternReason"] = pattern_reason
    enriched["normalizationRules"] = ["http-path-template-v1", f"{record.get('concept')}-pattern-v1"]
    return enriched


def normalize_path(path: str) -> str:
    path = path.split("?", 1)[0].strip()
    if not path:
        return "/"
    path = re.sub(r"<(?:[^:<>]+:)?[^<>]+>", "{var}", path)
    path = re.sub(r":([A-Za-z_][A-Za-z0-9_]*)", "{var}", path)
    path = re.sub(r"\{[^}/]+\}", "{var}", path)
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
            str(record.get("extractedValue") or ""),
        ]
    )

    if concept == "http-cancellation":
        if method == "POST" and re.search(r"/(?:cancel|abort|stop|terminate|kill)$", normalized_path.lower()):
            return "post-subresource-cancel", "POST action subresource ending in a cancellation verb"
        if method == "POST" and has_cancel_word(combined_text):
            return "post-action-cancel", "POST route associated with cancellation wording"
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
