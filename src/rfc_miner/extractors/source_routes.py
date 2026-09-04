from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from ..fs_walk import iter_files
from ..http_semantics import classify_route
from ..models import evidence_record


SOURCE_SUFFIXES = {
    ".cjs",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".ts",
    ".tsx",
}

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    "target",
    "test",
    "tests",
    "__tests__",
    "spec",
    "specs",
    "mock",
    "mocks",
    "fixture",
    "fixtures",
    "example",
    "examples",
    "doc",
    "docs",
}

MAX_FILE_BYTES = 1_000_000


@dataclass(frozen=True)
class RoutePattern:
    name: str
    regex: re.Pattern[str]
    method: Callable[[re.Match[str]], str]
    path: Callable[[re.Match[str]], str]
    suffixes: frozenset[str] | None = None


ROUTE_PATTERNS = [
    RoutePattern(
        "js-router-method",
        re.compile(
            r"(?<!@)\b(?:app|router|routes|server)\.(?P<method>get|post|put|patch|delete)\s*\(\s*[`'\"](?P<path>/[^`'\"]+)[`'\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: match.group("path"),
        frozenset({".cjs", ".js", ".jsx", ".mjs", ".py", ".ts", ".tsx"}),
    ),
    RoutePattern(
        "decorator-method",
        re.compile(
            r"@(?:\w+\.)?(?P<method>get|post|put|patch|delete)\s*\(\s*[`'\"](?P<path>/?[^`'\"]+)[`'\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: ensure_slash(match.group("path")),
        frozenset({".java", ".js", ".jsx", ".kt", ".php", ".py", ".rb", ".ts", ".tsx"}),
    ),
    RoutePattern(
        "flask-route-methods",
        re.compile(
            r"@(?:\w+\.)?route\s*\(\s*['\"](?P<path>/[^'\"]+)['\"][\s\S]{0,220}?methods\s*=\s*\[[^\]]*['\"](?P<method>GET|POST|PUT|PATCH|DELETE)['\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: match.group("path"),
        frozenset({".py"}),
    ),
    RoutePattern(
        "spring-short-mapping",
        re.compile(
            r"@(?P<method>Get|Post|Put|Patch|Delete)Mapping\s*\(\s*(?:(?:path|value)\s*=\s*)?['\"](?P<path>/[^'\"]+)['\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method").removesuffix("Mapping"),
        lambda match: match.group("path"),
        frozenset({".java", ".kt"}),
    ),
    RoutePattern(
        "spring-request-mapping",
        re.compile(
            r"@RequestMapping\s*\([\s\S]{0,260}?method\s*=\s*RequestMethod\.(?P<method>GET|POST|PUT|PATCH|DELETE)[\s\S]{0,260}?(?:path|value)\s*=\s*['\"](?P<path>/[^'\"]+)['\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: match.group("path"),
        frozenset({".java", ".kt"}),
    ),
    RoutePattern(
        "go-chi-gin-method",
        re.compile(
            r"\.(?P<method>GET|POST|PUT|PATCH|DELETE)\s*\(\s*[`'\"](?P<path>/[^`'\"]+)[`'\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: match.group("path"),
        frozenset({".go"}),
    ),
    RoutePattern(
        "go-handlefunc-method-path",
        re.compile(
            r"HandleFunc\s*\(\s*[`'\"](?P<method>GET|POST|PUT|PATCH|DELETE)\s+(?P<path>/[^`'\"]+)[`'\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: match.group("path"),
        frozenset({".go"}),
    ),
    RoutePattern(
        "rails-route",
        re.compile(
            r"\b(?P<method>get|post|put|patch|delete)\s+['\"](?P<path>/[^'\"]+)['\"]",
            re.IGNORECASE,
        ),
        lambda match: match.group("method"),
        lambda match: match.group("path"),
        frozenset({".rb"}),
    ),
]


def extract_source_routes(repo: dict[str, Any], repo_root: str | Path) -> list[dict[str, Any]]:
    root = Path(repo_root)
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, str, str]] = set()
    for path in iter_source_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in ROUTE_PATTERNS:
            if pattern.suffixes is not None and path.suffix.lower() not in pattern.suffixes:
                continue
            for match in pattern.regex.finditer(text):
                method = pattern.method(match).upper()
                route_path = pattern.path(match)
                if not route_path.startswith("/"):
                    continue
                line = line_for_index(text, match.start())
                symbol = route_symbol(pattern.name, text, match.start(), match.end())
                operation_text = f"{route_path} {symbol or ''} {route_context(text, match.start())}"
                response_codes = response_codes_from_text(operation_text)
                for concept in classify_route(
                    method=method,
                    path=route_path,
                    response_codes=response_codes,
                    operation_text=operation_text,
                    operation_name=symbol,
                ):
                    key = (relative_path(root, path), line, method, route_path, concept["concept"])
                    if key in seen:
                        continue
                    seen.add(key)
                    records.append(
                        evidence_record(
                            repository=repo["repo_id"],
                            commit=repo.get("commit_hash"),
                            concept=concept["concept"],
                            evidence_type="route",
                            http_method=method,
                            path=route_path,
                            response_codes=response_codes,
                            file=relative_path(root, path),
                            line_start=line,
                            line_end=line,
                            symbol=symbol,
                            confidence=max(0.1, concept["confidence"] - 0.08),
                            extracted_value={
                                "routePattern": pattern.name,
                                "classificationReason": concept["reason"],
                            },
                            extractor="source-routes",
                        )
                    )
    return records


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in iter_files(root, IGNORED_DIRS):
        try:
            is_file = path.is_file()
        except OSError:
            continue
        if not is_file or path.suffix.lower() not in SOURCE_SUFFIXES or is_test_file(path):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def is_test_file(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.go")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or name.endswith("tests.py")
    )


def response_codes_from_text(text: str) -> list[int]:
    codes: set[int] = set()
    if re.search(r"\b(?:HTTP_)?202(?:_ACCEPTED)?\b|Status202Accepted|StatusAccepted|http\.StatusAccepted", text):
        codes.add(202)
    for match in re.finditer(r"\b(?:status|code|writeHead|sendStatus)\s*\(?\s*(?P<code>[1-5][0-9]{2})\b", text):
        codes.add(int(match.group("code")))
    for match in re.finditer(r"\b(?P<code>[1-5][0-9]{2})\b", text):
        code = int(match.group("code"))
        if code in {200, 201, 202, 204, 400, 404, 409, 422, 429, 500, 503}:
            codes.add(code)
    return sorted(codes)


def route_context(text: str, start: int) -> str:
    lines = text.splitlines()
    line_index = line_for_index(text, start) - 1
    selected: list[str] = []
    for offset, line in enumerate(lines[line_index : line_index + 20]):
        selected.append(line)
        if offset > 0 and re.search(r"\}\s*\)\s*;?\s*$|\)\s*;?\s*$|^\s*}\s*$", line):
            break
    return "\n".join(selected)


def nearest_symbol(text: str, index: int) -> str | None:
    prefix = text[:index]
    lines = prefix.splitlines()[-25:]
    patterns = [
        re.compile(r"\bfunction\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\bdef\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\bfunc\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\bclass\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\b(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\("),
    ]
    for line in reversed(lines):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return match.group("symbol")
    return None


def route_symbol(pattern_name: str, text: str, start: int, end: int) -> str | None:
    if pattern_name in {"decorator-method", "flask-route-methods", "spring-short-mapping", "spring-request-mapping"}:
        return following_symbol(text, end) or nearest_symbol(text, start)
    return nearest_symbol(text, start)


def following_symbol(text: str, index: int) -> str | None:
    suffix = text[index:]
    lines = suffix.splitlines()[:12]
    patterns = [
        re.compile(r"\b(?:async\s+)?def\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\b(?:async\s+)?function\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\bfunc\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"),
        re.compile(r"\b(?:async\s+)?(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)\s*\("),
        re.compile(
            r"\b(?:public|private|protected|static|final|suspend|\s)+[A-Za-z0-9_<>, ?]+"
            r"\s+(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)\s*\("
        ),
    ]
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("@"):
            continue
        for pattern in patterns:
            match = pattern.search(stripped)
            if match:
                return match.group("symbol")
    return None


def line_for_index(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def ensure_slash(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
