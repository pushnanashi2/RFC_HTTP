from __future__ import annotations

import re
from typing import Any


ASYNC_NOUNS = {
    "allocation",
    "allocations",
    "backfill",
    "backfills",
    "job",
    "jobs",
    "operation",
    "operations",
    "task",
    "tasks",
    "run",
    "runs",
    "execution",
    "executions",
    "workflow",
    "workflows",
    "build",
    "builds",
    "deployment",
    "deployments",
    "pipeline",
    "pipelines",
    "dagrun",
    "dagruns",
}

CANCELABLE_RESOURCE_NOUNS = {
    "allocation",
    "allocations",
    "backfill",
    "backfills",
    "build",
    "builds",
    "deployment",
    "deployments",
    "execution",
    "executions",
    "job",
    "jobs",
    "operation",
    "operations",
    "run",
    "runs",
    "task",
    "tasks",
}

CANCEL_WORDS = {
    "cancel",
    "cancellation",
    "abort",
    "stop",
    "terminate",
    "kill",
}

STATUS_WORDS = {
    "status",
    "state",
    "progress",
    "result",
    "results",
}


def route_text(path: str, operation: dict[str, Any] | None = None) -> str:
    if not operation:
        return path
    fragments = [path]
    for key in ("operationId", "summary", "description"):
        value = operation.get(key)
        if isinstance(value, str):
            fragments.append(value)
    tags = operation.get("tags")
    if isinstance(tags, list):
        fragments.extend(str(tag) for tag in tags)
    return " ".join(fragments)


def classify_route(
    *,
    method: str,
    path: str,
    response_codes: list[int] | None = None,
    operation_text: str = "",
    operation_name: str | None = None,
) -> list[dict[str, Any]]:
    method = method.upper()
    codes = set(response_codes or [])
    path_lower = path.lower()
    combined = f"{path_lower} {operation_text.lower()}"
    segments = tokens(combined)
    path_segments = tokens(path_lower)
    name_segments = tokens(operation_name or "")
    concepts: list[dict[str, Any]] = []

    cancel_hit = bool(segments & CANCEL_WORDS)
    async_hit = bool(segments & ASYNC_NOUNS)
    status_hit = bool(segments & STATUS_WORDS)
    cancel_in_path = bool(path_segments & CANCEL_WORDS)
    cancel_in_name = bool(name_segments & CANCEL_WORDS)
    async_in_path = bool(path_segments & ASYNC_NOUNS)
    async_in_name = bool(name_segments & ASYNC_NOUNS)
    status_in_path = bool(path_segments & STATUS_WORDS)
    query_action_in_path = bool(path_segments & {"count", "filter", "list", "paginate", "search", "history"})

    if cancel_in_path and async_hit and (method in {"GET", "POST", "PUT", "PATCH", "DELETE"}):
        concepts.append(
            {
                "concept": "http-cancellation",
                "confidence": 0.96 if method in {"POST", "DELETE", "PATCH"} else 0.82,
                "reason": "cancel-word-with-async-resource",
            }
        )
    elif cancel_in_path and method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        concepts.append(
            {
                "concept": "http-cancellation",
                "confidence": 0.78,
                "reason": "cancel-word",
            }
        )
    elif cancel_in_name and async_in_path and method in {"POST", "PUT", "PATCH", "DELETE"}:
        concepts.append(
            {
                "concept": "http-cancellation",
                "confidence": 0.7,
                "reason": "operation-name-cancel-on-async-resource",
            }
        )
    elif method == "DELETE" and bool(path_segments & CANCELABLE_RESOURCE_NOUNS):
        concepts.append(
            {
                "concept": "http-cancellation",
                "confidence": 0.64,
                "reason": "delete-async-resource",
            }
        )

    if 202 in codes and method in {"POST", "PUT", "PATCH", "DELETE"}:
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.92,
                "reason": "accepted-response",
            }
        )
    elif async_hit and method == "POST" and not query_action_in_path and (async_in_path or async_in_name or 202 in codes):
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.78,
                "reason": "post-async-resource",
            }
        )
    elif method == "GET" and async_in_path and (status_hit or status_in_path):
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.86,
                "reason": "status-resource",
            }
        )
    elif method == "GET" and async_in_path:
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.68,
                "reason": "get-async-resource",
            }
        )

    return concepts


def has_async_noun(value: str) -> bool:
    return bool(tokens(value) & ASYNC_NOUNS)


def has_cancel_word(value: str) -> bool:
    return bool(tokens(value) & CANCEL_WORDS)


def has_status_word(value: str) -> bool:
    return bool(tokens(value) & STATUS_WORDS)


def tokens(value: str) -> set[str]:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return {segment for segment in re.split(r"[^a-z0-9]+", separated.lower()) if segment}
