from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .collector import parse_github_url
from .io import read_json, write_json


DEFAULT_LANGUAGES = [
    "Go",
    "TypeScript",
    "Python",
    "Java",
    "JavaScript",
    "Rust",
    "Ruby",
    "PHP",
    "C#",
    "Kotlin",
    "Scala",
    "Elixir",
]

DEFAULT_TERMS = [
    "workflow",
    "scheduler",
    "orchestration",
    "job queue",
    "pipeline",
    "webhook",
    "kubernetes",
    "\"developer platform\"",
    "\"cloud native\"",
    "automation",
    "\"long running\"",
    "idempotency",
    "\"async operation\"",
    "task runner",
    "api server",
    "\"rest api\"",
    "openapi server",
    "swagger server",
]

DEFAULT_MAX_SIZE_KB = 250_000

STRONG_SERVER_MARKERS = {
    "api server",
    "backend",
    "cloud native",
    "controller",
    "developer platform",
    "distributed",
    "gateway",
    "job",
    "job queue",
    "kubernetes",
    "operator",
    "orchestration",
    "pipeline",
    "rest api",
    "scheduler",
    "server",
    "service",
    "webhook",
    "workflow engine",
}

DOMAIN_MARKERS = {
    "async operation",
    "idempotency",
    "long running",
    "task runner",
    "workflow",
}

SDK_ONLY_MARKERS = {
    "api client",
    "api-client",
    "client library",
    "client sdk",
    "client-sdk",
    "codegen",
    "generated client",
    "generated sdk",
    "http client",
    "kiota",
    "openapi generator",
    "openapi-generator",
    "sdk",
    "swagger codegen",
    "swagger-codegen",
}

TOY_MARKERS = {
    "awesome",
    "demo",
    "demos",
    "example",
    "examples",
    "sample",
    "samples",
    "starter",
    "template",
    "templates",
    "tutorial",
}

NON_SERVER_REPOSITORY_MARKERS = {
    "alfred",
    "awesome",
    "cheatsheet",
    "font-awesome",
    "github-action",
    "github-actions",
    "notebook",
    "obsidian",
    "paper",
    "prompt",
    "prompts",
    "roadmap",
    "sample",
    "samples",
    "starter",
    "template",
    "templates",
    "tutorial",
    "wallpaper",
    "workflow-template",
    "workflow-templates",
    "workflow_template",
    "workflow_templates",
}

NON_SERVER_CONTENT_MARKERS = {
    "alfred workflow",
    "browser extension",
    "chrome extension",
    "comfyui",
    "desktop app",
    "figma",
    "jetbrains",
    "obsidian",
    "paper reading",
    "prompt",
    "prompts",
    "vscode",
    "wallpaper",
}


def discover_github_repositories(
    *,
    output_path: str | Path,
    target: int,
    min_stars: int = 20,
    updated_since: str = "2024-01-01",
    languages: list[str] | None = None,
    terms: list[str] | None = None,
    per_query_limit: int = 200,
    max_size_kb: int = DEFAULT_MAX_SIZE_KB,
    resume: bool = True,
) -> dict[str, Any]:
    output = Path(output_path)
    existing = read_json(output, default={"repositories": [], "queries": []}) if resume else {"repositories": [], "queries": []}
    repositories = list(existing.get("repositories") or [])
    seen = {record["repository_url"].rstrip("/") for record in repositories if record.get("repository_url")}
    completed_queries = {query["query"] for query in existing.get("queries") or [] if query.get("completed")}
    query_records = list(existing.get("queries") or [])

    for query in build_queries(
        languages=languages or DEFAULT_LANGUAGES,
        terms=terms or DEFAULT_TERMS,
        min_stars=min_stars,
        updated_since=updated_since,
        max_size_kb=max_size_kb,
    ):
        if len(repositories) >= target:
            break
        if query in completed_queries:
            continue

        before = len(repositories)
        for item in search_repositories(query=query, limit=per_query_limit):
            seed = seed_from_search_item(item, max_size_kb=max_size_kb)
            if not seed:
                continue
            key = seed["repository_url"].rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            repositories.append(seed)
            if len(repositories) >= target:
                break

        query_records.append(
            {
                "query": query,
                "completed": True,
                "newRepositories": len(repositories) - before,
                "totalRepositories": len(repositories),
            }
        )
        write_json(
            output,
            {
                "target": target,
                "repositories": repositories[:target],
                "queries": query_records,
            },
        )

    result = {
        "target": target,
        "repositories": repositories[:target],
        "queries": query_records,
    }
    write_json(output, result)
    return result


def build_queries(
    *,
    languages: list[str],
    terms: list[str],
    min_stars: int,
    updated_since: str,
    max_size_kb: int = DEFAULT_MAX_SIZE_KB,
) -> list[str]:
    queries: list[str] = []
    for term in terms:
        for language in languages:
            queries.append(
                f"{term} language:{language} stars:>={min_stars} pushed:>={updated_since} size:<{max_size_kb} archived:false fork:false"
            )
    for term in terms:
        queries.append(
            f"{term} stars:>={min_stars * 5} pushed:>={updated_since} size:<{max_size_kb} archived:false fork:false"
        )
    return queries


def search_repositories(*, query: str, limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    per_page = 100
    page = 1
    while len(items) < limit:
        requested = min(per_page, limit - len(items))
        params = urllib.parse.urlencode(
            {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": requested,
                "page": page,
            }
        )
        url = f"https://api.github.com/search/repositories?{params}"
        response = github_get(url)
        batch = response.get("items") or []
        if not batch:
            break
        items.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < requested or page >= 10:
            break
        page += 1
    return items


def github_get(url: str) -> dict[str, Any]:
    while True:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "rfc-http-miner/0.1.0",
                "X-GitHub-Api-Version": "2022-11-28",
                **auth_header(),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                throttle_if_needed(response.headers)
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in {403, 429}:
                reset = int(error.headers.get("x-ratelimit-reset") or "0")
                sleep_until_reset(reset)
                continue
            raise


def throttle_if_needed(headers: Any) -> None:
    remaining = headers.get("x-ratelimit-remaining")
    reset = headers.get("x-ratelimit-reset")
    if remaining == "0" and reset:
        sleep_until_reset(int(reset))


def sleep_until_reset(reset: int) -> None:
    delay = max(1, reset - int(time.time()) + 2)
    time.sleep(delay)


def auth_header() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def seed_from_search_item(item: dict[str, Any], *, max_size_kb: int = DEFAULT_MAX_SIZE_KB) -> dict[str, Any] | None:
    if not should_include_item(item, max_size_kb=max_size_kb):
        return None
    html_url = item.get("html_url") or item.get("url")
    if not isinstance(html_url, str) or not html_url.startswith("https://github.com/"):
        return None
    try:
        owner_name, repo_name = parse_github_url(html_url)
    except ValueError:
        return None
    owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
    vendor = owner.get("login") or owner_name
    license_value = item.get("license") if isinstance(item.get("license"), dict) else {}
    topics = item.get("topics") if isinstance(item.get("topics"), list) else []
    return {
        "repository_url": html_url,
        "owner": owner_name,
        "name": repo_name,
        "language": item.get("language"),
        "framework": infer_framework(item),
        "stars": item.get("stargazers_count"),
        "forks": item.get("forks_count"),
        "license": license_value.get("spdx_id") or license_value.get("key"),
        "last_activity": item.get("pushed_at") or item.get("updated_at"),
        "default_branch": item.get("default_branch"),
        "project_category": infer_project_category(item),
        "fork_parent": None,
        "probable_template": probable_template(item),
        "probable_origin": None,
        "vendor": vendor,
        "size_kb": item.get("size"),
        "discovery_topics": topics[:20],
        "discovery_description": item.get("description"),
    }


def infer_framework(item: dict[str, Any]) -> str | None:
    haystack = search_haystack(item)
    framework_markers = {
        "fastapi": "fastapi",
        "django": "django",
        "flask": "flask",
        "express": "express",
        "nestjs": "nestjs",
        "spring": "spring",
        "rails": "rails",
        "gin": "gin",
        "chi": "chi",
        "actix": "actix",
        "axum": "axum",
        "laravel": "laravel",
        "phoenix": "phoenix",
    }
    for marker, framework in framework_markers.items():
        if marker in haystack:
            return framework
    return item.get("language")


def infer_project_category(item: dict[str, Any]) -> str | None:
    haystack = search_haystack(item)
    categories = {
        "workflow": "workflow-engine",
        "orchestration": "orchestration-engine",
        "scheduler": "job-scheduler",
        "pipeline": "ci-orchestration",
        "kubernetes": "cloud-native",
        "webhook": "developer-platform",
        "openapi": "api-server",
        "swagger": "api-server",
        "api gateway": "api-gateway",
    }
    for marker, category in categories.items():
        if marker in haystack:
            return category
    return "api-candidate"


def probable_template(item: dict[str, Any]) -> str | None:
    haystack = search_haystack(item)
    for marker in ("template", "starter", "scaffold", "sample", "demo", "example"):
        if marker in haystack:
            return "metadata-indicator"
    if any(marker in haystack for marker in SDK_ONLY_MARKERS):
        return "generated-sdk-suspect"
    return None


def should_include_item(item: dict[str, Any], *, max_size_kb: int = DEFAULT_MAX_SIZE_KB) -> bool:
    if item.get("archived") is True or item.get("isArchived") is True:
        return False
    if item.get("fork") is True or item.get("isFork") is True:
        return False
    if item.get("private") is True or item.get("isPrivate") is True:
        return False
    size = item.get("size")
    if isinstance(size, int) and size >= max_size_kb:
        return False
    haystack = search_haystack(item)
    name = str(item.get("name") or "").lower()
    full_name = str(item.get("full_name") or "").lower()
    name_haystack = f"{name} {full_name}"
    content_haystack = search_content_haystack(item)
    hard_non_server = any(marker in name_haystack for marker in NON_SERVER_REPOSITORY_MARKERS)
    content_non_server = any(marker in content_haystack for marker in NON_SERVER_CONTENT_MARKERS)
    github_action_like = "github action" in haystack or "github actions" in haystack or name.startswith("setup-")
    cli_like = name == "cli" or name.endswith("-cli") or name.endswith("_cli") or " command line " in f" {haystack} "
    if hard_non_server or content_non_server or github_action_like or cli_like:
        return False
    server_like = any(marker in haystack for marker in STRONG_SERVER_MARKERS)
    domain_like = any(marker in haystack for marker in DOMAIN_MARKERS)
    sdk_like = any(marker in haystack for marker in SDK_ONLY_MARKERS)
    toy_like = any(marker in content_haystack for marker in TOY_MARKERS)
    if toy_like:
        return False
    if sdk_like:
        return False
    if name.endswith(("-sdk", "-client", "_sdk", "_client")):
        return False
    return server_like or domain_like


def search_haystack(item: dict[str, Any]) -> str:
    topics = item.get("topics") if isinstance(item.get("topics"), list) else []
    parts = [
        str(item.get("name") or ""),
        str(item.get("full_name") or ""),
        str(item.get("description") or ""),
        " ".join(str(topic) for topic in topics),
    ]
    return " ".join(parts).lower()


def search_content_haystack(item: dict[str, Any]) -> str:
    topics = item.get("topics") if isinstance(item.get("topics"), list) else []
    parts = [
        str(item.get("name") or ""),
        str(item.get("description") or ""),
        " ".join(str(topic) for topic in topics),
    ]
    return " ".join(parts).lower()
