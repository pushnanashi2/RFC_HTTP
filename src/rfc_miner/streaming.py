from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .collector import (
    clone_or_update,
    command_error_message,
    default_branch_from_checkout,
    fetch_github_metadata,
    git_output,
    load_seed,
    probable_template_name,
)
from .extraction import analyze_repository
from .io import write_jsonl
from .models import error_record, repository_record
from .paths import DataPaths, ensure_data_dirs


def collect_and_analyze_streaming(
    *,
    seed_path: str | Path,
    paths: DataPaths,
    repo_dir: str | Path,
    limit: int | None = None,
    keep_repos: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ensure_data_dirs(paths)
    repo_root = Path(repo_dir)
    repo_root.mkdir(parents=True, exist_ok=True)
    seed = load_seed(seed_path)
    if limit is not None:
        seed = seed[:limit]

    repositories: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for item in seed:
        repo, repo_errors = collect_one(item, repo_root)
        repositories.append(repo)
        errors.extend(repo_errors)

        if repo.get("local_path"):
            repo_evidence, analyze_errors = analyze_repository(repo)
            evidence.extend(repo_evidence)
            errors.extend(analyze_errors)

        if not keep_repos and repo.get("local_path"):
            cleanup_checkout(Path(str(repo["local_path"])), repo_root)
            repo["local_path"] = None

        write_jsonl(paths.repositories, repositories)
        write_jsonl(paths.raw_evidence, evidence)
        write_jsonl(paths.errors, errors)

    return repositories, evidence, errors


def collect_one(item: dict[str, Any], repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    owner = str(item["owner"])
    name = str(item["name"])
    repository_url = str(item["repository_url"])
    repo_id = f"{owner}/{name}"
    metadata = fetch_github_metadata(owner, name)
    errors: list[dict[str, Any]] = []

    local_path = item.get("local_path")
    commit_hash = item.get("commit_hash")
    default_branch = item.get("default_branch") or metadata.get("default_branch")

    if not local_path:
        destination = repo_root / f"{owner}__{name}"
        try:
            clone_or_update(repository_url, destination)
            local_path = str(destination)
            commit_hash = git_output(["git", "rev-parse", "HEAD"], cwd=destination)
            if not default_branch:
                default_branch = default_branch_from_checkout(destination)
        except subprocess.CalledProcessError as error:
            errors.append(
                error_record(
                    repo=repo_id,
                    stage="collect",
                    error_type="git_clone_failed",
                    error=command_error_message(error),
                    retryable=True,
                )
            )
            cleanup_checkout(destination, repo_root)
            local_path = None

    license_value = metadata.get("license")
    license_name = None
    if isinstance(license_value, dict):
        license_name = license_value.get("spdx_id") or license_value.get("key")

    parent = metadata.get("parent") if isinstance(metadata.get("parent"), dict) else None
    fork_parent = parent.get("full_name") if parent else item.get("fork_parent")
    probable_template = item.get("probable_template") or probable_template_name(owner, name)

    repo = repository_record(
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
    return repo, errors


def cleanup_checkout(path: Path, repo_root: Path) -> None:
    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return
    if path.exists():
        shutil.rmtree(path)
