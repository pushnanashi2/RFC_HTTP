from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .io import write_jsonl
from .models import repository_record
from .paths import DataPaths, ensure_data_dirs


GITHUB_RE = re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<name>[^/#?]+?)(?:\.git)?/?$")


def parse_github_url(url: str) -> tuple[str, str]:
    match = GITHUB_RE.match(url.strip())
    if not match:
        raise ValueError(f"unsupported GitHub repository URL: {url}")
    return match.group("owner"), match.group("name")


def load_seed(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if isinstance(value, dict):
        records = value.get("repositories", [])
    else:
        records = value
    if not isinstance(records, list):
        raise ValueError("seed must be a list or an object with repositories")

    normalized: list[dict[str, Any]] = []
    for item in records:
        if isinstance(item, str):
            owner, name = parse_github_url(item)
            normalized.append({"repository_url": item, "owner": owner, "name": name})
        elif isinstance(item, dict):
            repository_url = str(item.get("repository_url") or item.get("url") or "")
            if not repository_url:
                raise ValueError(f"seed item is missing repository_url: {item}")
            owner = item.get("owner")
            name = item.get("name")
            if not owner or not name:
                owner, name = parse_github_url(repository_url)
            merged = dict(item)
            merged["repository_url"] = repository_url
            merged["owner"] = owner
            merged["name"] = name
            normalized.append(merged)
        else:
            raise ValueError(f"unsupported seed item: {item!r}")
    return normalized


def fetch_github_metadata(owner: str, name: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{name}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rfc-http-miner/0.1.0",
            **_auth_header(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return {}


def _auth_header() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def collect_repositories(
    *,
    seed_path: str | Path,
    paths: DataPaths,
    repo_dir: str | Path,
    limit: int | None = None,
    clone: bool = True,
) -> list[dict[str, Any]]:
    ensure_data_dirs(paths)
    repo_root = Path(repo_dir)
    repo_root.mkdir(parents=True, exist_ok=True)

    seed = load_seed(seed_path)
    if limit is not None:
        seed = seed[:limit]

    records: list[dict[str, Any]] = []
    for item in seed:
        owner = str(item["owner"])
        name = str(item["name"])
        repository_url = str(item["repository_url"])
        metadata = fetch_github_metadata(owner, name)
        local_path = item.get("local_path")
        commit_hash = item.get("commit_hash")
        default_branch = item.get("default_branch") or metadata.get("default_branch")

        if clone and not local_path:
            destination = repo_root / f"{owner}__{name}"
            clone_or_update(repository_url, destination)
            local_path = str(destination)
            commit_hash = git_output(["git", "rev-parse", "HEAD"], cwd=destination)
            if not default_branch:
                default_branch = default_branch_from_checkout(destination)

        license_value = metadata.get("license")
        license_name = None
        if isinstance(license_value, dict):
            license_name = license_value.get("spdx_id") or license_value.get("key")

        parent = metadata.get("parent") if isinstance(metadata.get("parent"), dict) else None
        fork_parent = parent.get("full_name") if parent else item.get("fork_parent")
        probable_template = item.get("probable_template") or probable_template_name(owner, name)

        records.append(
            repository_record(
                repository_url=repository_url,
                owner=owner,
                name=name,
                language=item.get("language") or metadata.get("language"),
                framework=item.get("framework"),
                stars=item.get("stars") if item.get("stars") is not None else metadata.get("stargazers_count"),
                forks=item.get("forks") if item.get("forks") is not None else metadata.get("forks_count"),
                license_name=item.get("license") or license_name,
                last_activity=item.get("last_activity") or metadata.get("pushed_at"),
                default_branch=default_branch,
                commit_hash=commit_hash,
                project_category=item.get("project_category"),
                fork_parent=fork_parent,
                probable_template=probable_template,
                probable_origin=item.get("probable_origin") or fork_parent,
                vendor=item.get("vendor") or owner,
                local_path=local_path,
            )
        )

    write_jsonl(paths.repositories, records)
    return records


def clone_or_update(repository_url: str, destination: Path) -> None:
    if (destination / ".git").exists():
        git_output(["git", "fetch", "--depth", "1", "origin"], cwd=destination)
        git_output(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=destination)
        return
    subprocess.run(
        ["git", "clone", "--depth", "1", repository_url, str(destination)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def git_output(command: list[str], cwd: str | Path) -> str:
    result = subprocess.run(
        command,
        cwd=str(cwd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def default_branch_from_checkout(path: Path) -> str | None:
    try:
        symbolic = git_output(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=path)
    except subprocess.CalledProcessError:
        return None
    return symbolic.rsplit("/", 1)[-1] if symbolic else None


def probable_template_name(owner: str, name: str) -> str | None:
    lowered = f"{owner}/{name}".lower()
    indicators = ["template", "starter", "scaffold", "example", "demo", "sample"]
    if any(indicator in lowered for indicator in indicators):
        return "name-indicator"
    if lowered.endswith("-sdk") or "/sdk-" in lowered:
        return "generated-sdk-suspect"
    return None
