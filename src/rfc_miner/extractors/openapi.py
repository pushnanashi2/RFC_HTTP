from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..fs_walk import iter_files
from ..http_semantics import classify_route, route_text
from ..models import evidence_record


METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
OPENAPI_NAME_RE = re.compile(r"(openapi|swagger)", re.IGNORECASE)


def extract_openapi(repo: dict[str, Any], repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root)
    records: list[dict[str, Any]] = []
    for path in iter_openapi_files(root):
        try:
            if path.suffix.lower() == ".json":
                records.extend(extract_openapi_json(repo, root, path))
            else:
                records.extend(extract_openapi_yaml(repo, root, path))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
    return records


def iter_openapi_files(root: Path) -> Iterable[Path]:
    ignored = {".git", "node_modules", "vendor", "dist", "build", ".venv", "venv"}
    for path in iter_files(root, ignored):
        try:
            is_file = path.is_file()
        except OSError:
            continue
        if not is_file:
            continue
        lowered = path.name.lower()
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        if OPENAPI_NAME_RE.search(lowered) or lowered in {"api.json", "api.yaml", "api.yml"}:
            yield path


def extract_openapi_json(repo: dict[str, Any], root: Path, path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    document = json.loads(text)
    if not isinstance(document, dict):
        return []
    paths = document.get("paths")
    if not isinstance(paths, dict):
        return []

    records: list[dict[str, Any]] = []
    for route_path, operations in paths.items():
        if not isinstance(route_path, str) or not isinstance(operations, dict):
            continue
        line = line_for_token(text, route_path)
        for method, operation in operations.items():
            if method.lower() not in METHODS or not isinstance(operation, dict):
                continue
            response_codes = response_codes_from_openapi(operation.get("responses"))
            operation_text = route_text(route_path, operation)
            for concept in classify_route(
                method=method,
                path=route_path,
                response_codes=response_codes,
                operation_text=operation_text,
                operation_name=operation.get("operationId"),
            ):
                records.append(
                    evidence_record(
                        repository=repo["repo_id"],
                        commit=repo.get("commit_hash"),
                        concept=concept["concept"],
                        evidence_type="openapi_operation",
                        http_method=method,
                        path=route_path,
                        response_codes=response_codes,
                        file=relative_path(root, path),
                        line_start=line,
                        symbol=operation.get("operationId"),
                        confidence=concept["confidence"],
                        extracted_value={
                            "operationId": operation.get("operationId"),
                            "summary": operation.get("summary"),
                            "description": operation.get("description"),
                            "responses": sorted(response_codes),
                            "classificationReason": concept["reason"],
                        },
                        extractor="openapi",
                    )
                )
    return records


def extract_openapi_yaml(repo: dict[str, Any], root: Path, path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    in_paths = False
    current_path: str | None = None
    current_path_line = 1
    current_method: str | None = None
    current_method_line = 1
    response_codes: set[int] = set()
    operation: dict[str, Any] = {}

    def flush() -> None:
        nonlocal current_method, response_codes, operation, current_method_line
        if not current_path or not current_method:
            return
        operation_text = route_text(current_path, operation)
        codes = sorted(response_codes)
        for concept in classify_route(
            method=current_method,
            path=current_path,
            response_codes=codes,
            operation_text=operation_text,
            operation_name=operation.get("operationId"),
        ):
            records.append(
                evidence_record(
                    repository=repo["repo_id"],
                    commit=repo.get("commit_hash"),
                    concept=concept["concept"],
                    evidence_type="openapi_operation",
                    http_method=current_method,
                    path=current_path,
                    response_codes=codes,
                    file=relative_path(root, path),
                    line_start=current_method_line,
                    symbol=operation.get("operationId"),
                    confidence=concept["confidence"],
                    extracted_value={
                        "operationId": operation.get("operationId"),
                        "summary": operation.get("summary"),
                        "description": operation.get("description"),
                        "responses": codes,
                        "classificationReason": concept["reason"],
                    },
                    extractor="openapi-yaml-lite",
                )
            )

    for index, line in enumerate(lines, start=1):
        if re.match(r"^paths\s*:\s*$", line):
            in_paths = True
            continue
        if in_paths and line and not line.startswith((" ", "\t")) and not line.startswith("paths:"):
            flush()
            break
        if not in_paths:
            continue

        path_match = re.match(r"^\s{1,8}['\"]?(?P<path>/[^:'\"]+)['\"]?\s*:\s*$", line)
        if path_match:
            flush()
            current_path = path_match.group("path").strip()
            current_path_line = index
            current_method = None
            response_codes = set()
            operation = {}
            continue

        method_match = re.match(r"^\s{2,12}(?P<method>get|post|put|patch|delete|options|head)\s*:\s*$", line)
        if method_match and current_path:
            flush()
            current_method = method_match.group("method")
            current_method_line = index
            response_codes = set()
            operation = {}
            continue

        if current_method:
            scalar_match = re.match(r"^\s+(?P<key>operationId|summary|description)\s*:\s*(?P<value>.+?)\s*$", line)
            if scalar_match:
                operation[scalar_match.group("key")] = scalar_match.group("value").strip("'\"")
            response_match = re.match(r"^\s+['\"]?(?P<code>[1-5][0-9]{2})['\"]?\s*:\s*$", line)
            if response_match:
                response_codes.add(int(response_match.group("code")))

    flush()
    return records


def response_codes_from_openapi(responses: Any) -> list[int]:
    if not isinstance(responses, dict):
        return []
    codes: list[int] = []
    for key in responses:
        if isinstance(key, int):
            codes.append(key)
        elif isinstance(key, str) and key.isdigit():
            codes.append(int(key))
    return sorted(set(codes))


def line_for_token(text: str, token: str) -> int:
    index = text.find(json.dumps(token))
    if index < 0:
        index = text.find(token)
    if index < 0:
        return 1
    return text.count("\n", 0, index) + 1


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
