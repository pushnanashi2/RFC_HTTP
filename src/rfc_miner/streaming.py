from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from .io import read_jsonl, write_jsonl
from .models import error_record, repository_record
from .paths import DataPaths, ensure_data_dirs


def collect_and_analyze_streaming(
    *,
    seed_path: str | Path,
    paths: DataPaths,
    repo_dir: str | Path,
    limit: int | None = None,
    keep_repos: bool = False,
    resume: bool = True,
    progress: bool = True,
    jobs: int = 1,
    flush_interval: int = 25,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    ensure_data_dirs(paths)
    repo_root = Path(repo_dir)
    repo_root.mkdir(parents=True, exist_ok=True)
    seed = load_seed(seed_path)
    if limit is not None:
        seed = seed[:limit]

    repositories = read_jsonl(paths.repositories) if resume else []
    evidence = read_jsonl(paths.raw_evidence) if resume else []
    errors = read_jsonl(paths.errors) if resume else []
    if resume:
        repositories, evidence, errors = prune_retryable_records(repositories, evidence, errors)
    seed_order = {repo_id(item): index for index, item in enumerate(seed, start=1)}
    processed = {str(record.get("repo_id")) for record in repositories if record.get("repo_id")}
    pending = [(index, item) for index, item in enumerate(seed, start=1) if repo_id(item) not in processed]

    if jobs <= 1:
        completed_since_flush = 0
        for index, item in pending:
            item_repo_id = repo_id(item)
            repo, repo_evidence, repo_errors = collect_analyze_one(item, repo_root, keep_repos)
            repositories.append(repo)
            evidence.extend(repo_evidence)
            errors.extend(repo_errors)
            processed.add(item_repo_id)
            completed_since_flush += 1
            if completed_since_flush >= flush_interval:
                write_stream_outputs(paths, repositories, evidence, errors, seed_order)
                completed_since_flush = 0
            print_progress(progress, index, len(seed), item_repo_id, len(repo_evidence), len(repo_errors))
        write_stream_outputs(paths, repositories, evidence, errors, seed_order)
        return repositories, evidence, errors

    completed_since_flush = 0
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(collect_analyze_one, item, repo_root, keep_repos): (index, item)
            for index, item in pending
        }
        for future in as_completed(futures):
            index, item = futures[future]
            item_repo_id = repo_id(item)
            try:
                repo, repo_evidence, repo_errors = future.result()
            except Exception as error:  # noqa: BLE001 - corpus runs must isolate repo failures
                repo = failed_repository_record(item)
                repo_evidence = []
                repo_errors = [
                    error_record(
                        repo=item_repo_id,
                        stage="run",
                        error_type=error.__class__.__name__,
                        error=str(error),
                        retryable=False,
                    )
                ]
            repositories.append(repo)
            evidence.extend(repo_evidence)
            errors.extend(repo_errors)
            processed.add(item_repo_id)
            completed_since_flush += 1
            if completed_since_flush >= flush_interval:
                write_stream_outputs(paths, repositories, evidence, errors, seed_order)
                completed_since_flush = 0
            print_progress(progress, index, len(seed), item_repo_id, len(repo_evidence), len(repo_errors))

    write_stream_outputs(paths, repositories, evidence, errors, seed_order)
    return repositories, evidence, errors


def collect_analyze_one(
    item: dict[str, Any],
    repo_root: Path,
    keep_repos: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    repo, repo_errors = collect_one(item, repo_root)
    evidence: list[dict[str, Any]] = []
    errors = list(repo_errors)

    if repo.get("local_path"):
        repo_evidence, analyze_errors = analyze_repository(repo)
        evidence.extend(repo_evidence)
        errors.extend(analyze_errors)

    if not keep_repos and repo.get("local_path"):
        cleanup_checkout(Path(str(repo["local_path"])), repo_root)
        repo["local_path"] = None

    return repo, evidence, errors


def collect_one(item: dict[str, Any], repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    owner = str(item["owner"])
    name = str(item["name"])
    repository_url = str(item["repository_url"])
    item_repo_id = f"{owner}/{name}"
    metadata = {} if has_seed_metadata(item) else fetch_github_metadata(owner, name)
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
                    repo=item_repo_id,
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


def write_stream_outputs(
    paths: DataPaths,
    repositories: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    seed_order: dict[str, int],
) -> None:
    write_jsonl(
        paths.repositories,
        sorted(repositories, key=lambda record: seed_order.get(str(record.get("repo_id")), 10**12)),
    )
    write_jsonl(
        paths.raw_evidence,
        sorted(
            evidence,
            key=lambda record: (
                seed_order.get(str(record.get("repository")), 10**12),
                str(record.get("file") or ""),
                int(record.get("lineStart") or 0),
                str(record.get("httpMethod") or ""),
                str(record.get("path") or ""),
                str(record.get("concept") or ""),
            ),
        ),
    )
    write_jsonl(
        paths.errors,
        sorted(
            errors,
            key=lambda record: (
                seed_order.get(str(record.get("repo")), 10**12),
                str(record.get("stage") or ""),
                str(record.get("errorType") or ""),
                str(record.get("error") or ""),
            ),
        ),
    )


def prune_retryable_records(
    repositories: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    retryable_repo_ids = {
        str(record.get("repo"))
        for record in errors
        if record.get("retryable") is True and record.get("repo")
    }
    if not retryable_repo_ids:
        return repositories, evidence, errors
    return (
        [record for record in repositories if str(record.get("repo_id")) not in retryable_repo_ids],
        [record for record in evidence if str(record.get("repository")) not in retryable_repo_ids],
        [record for record in errors if str(record.get("repo")) not in retryable_repo_ids],
    )


def print_progress(
    enabled: bool,
    index: int,
    total: int,
    repository: str,
    evidence_delta: int,
    error_delta: int,
) -> None:
    if not enabled:
        return
    print(
        "progress: {done}/{total} {repo} evidence+{evidence_delta} errors+{error_delta}".format(
            done=index,
            total=total,
            repo=repository,
            evidence_delta=evidence_delta,
            error_delta=error_delta,
        ),
        flush=True,
    )


def repo_id(item: dict[str, Any]) -> str:
    return f"{item['owner']}/{item['name']}"


def failed_repository_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_id": repo_id(item),
        "repository_url": item.get("repository_url"),
        "owner": item.get("owner"),
        "name": item.get("name"),
        "language": item.get("language"),
        "framework": item.get("framework"),
        "stars": item.get("stars"),
        "forks": item.get("forks"),
        "license": item.get("license"),
        "last_activity": item.get("last_activity"),
        "default_branch": item.get("default_branch"),
        "commit_hash": item.get("commit_hash"),
        "project_category": item.get("project_category"),
        "fork_parent": item.get("fork_parent"),
        "probable_template": item.get("probable_template"),
        "probable_origin": item.get("probable_origin"),
        "vendor": item.get("vendor") or item.get("owner"),
        "collection_timestamp": None,
        "local_path": None,
    }


def has_seed_metadata(item: dict[str, Any]) -> bool:
    return any(key in item for key in ("stars", "forks", "license", "last_activity", "default_branch"))


def cleanup_checkout(path: Path, repo_root: Path) -> None:
    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return
    if path.exists():
        shutil.rmtree(path)
