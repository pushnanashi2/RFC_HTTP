from __future__ import annotations

import re
from typing import Any


ASYNC_NOUNS = {
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
) -> list[dict[str, Any]]:
    method = method.upper()
    codes = set(response_codes or [])
    path_lower = path.lower()
    combined = f"{path_lower} {operation_text.lower()}"
    segments = set(re.split(r"[^a-z0-9]+", combined))
    concepts: list[dict[str, Any]] = []

    cancel_hit = bool(segments & CANCEL_WORDS)
    async_hit = bool(segments & ASYNC_NOUNS)
    status_hit = bool(segments & STATUS_WORDS)

    if cancel_hit and async_hit:
        concepts.append(
            {
                "concept": "http-cancellation",
                "confidence": 0.96 if method in {"POST", "DELETE", "PATCH"} else 0.82,
                "reason": "cancel-word-with-async-resource",
            }
        )
    elif cancel_hit:
        concepts.append(
            {
                "concept": "http-cancellation",
                "confidence": 0.78,
                "reason": "cancel-word",
            }
        )
    elif method == "DELETE" and async_hit:
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
    elif async_hit and method == "POST":
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.78,
                "reason": "post-async-resource",
            }
        )
    elif async_hit and method == "GET" and status_hit:
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.86,
                "reason": "status-resource",
            }
        )
    elif async_hit and method == "GET":
        concepts.append(
            {
                "concept": "http-async-operation",
                "confidence": 0.68,
                "reason": "get-async-resource",
            }
        )

    return concepts


def has_async_noun(value: str) -> bool:
    segments = set(re.split(r"[^a-z0-9]+", value.lower()))
    return bool(segments & ASYNC_NOUNS)


def has_cancel_word(value: str) -> bool:
    segments = set(re.split(r"[^a-z0-9]+", value.lower()))
    return bool(segments & CANCEL_WORDS)


def has_status_word(value: str) -> bool:
    segments = set(re.split(r"[^a-z0-9]+", value.lower()))
    return bool(segments & STATUS_WORDS)
