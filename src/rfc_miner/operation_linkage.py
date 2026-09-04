from __future__ import annotations

from collections import defaultdict
from typing import Any

from .http_semantics import STATUS_WORDS, has_async_noun, tokens


STRICT_CANCELLATION_PATTERNS = frozenset(
    {
        "post-subresource-cancel",
        "post-action-cancel",
        "put-action-cancel",
        "get-cancel-link",
        "patch-state-cancelled",
        "delete-action-cancel",
    }
)

CANCEL_ACTION_PREFIXES = ("cancel", "abort", "stop", "terminate", "kill")


def cancellation_linkage_metrics(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    async_paths_by_repo = async_operation_paths_by_repo(
        evidence=evidence,
        family_by_repo=family_by_repo,
    )
    totals = new_totals()
    strict_totals = new_totals()
    pattern_totals: dict[str, dict[str, Any]] = defaultdict(new_totals)

    for record in evidence:
        if str(record.get("concept") or "") != "http-cancellation":
            continue
        repo_id = str(record.get("repository") or "")
        family_id = included_family_id(repo_id, family_by_repo)
        if family_id is None:
            continue

        pattern = str(record.get("pattern") or "unknown")
        linkage = cancellation_record_linkage(
            record=record,
            async_paths_by_repo=async_paths_by_repo,
        )

        add_record(totals, repo_id, family_id, linkage)
        add_record(pattern_totals[pattern], repo_id, family_id, linkage)
        if pattern in STRICT_CANCELLATION_PATTERNS:
            add_record(strict_totals, repo_id, family_id, linkage)

    return {
        "all": freeze_totals(totals),
        "strict": freeze_totals(strict_totals),
        "byPattern": {
            pattern: freeze_totals(metrics)
            for pattern, metrics in sorted(pattern_totals.items())
        },
        "operationResourceLinked": operation_resource_linked_metrics(
            strict_totals=strict_totals,
            delete_operation_totals=pattern_totals.get(
                "delete-operation-resource",
                new_totals(),
            ),
        ),
    }


def cancellation_record_linkage(
    *,
    record: dict[str, Any],
    async_paths_by_repo: dict[str, set[str]],
) -> dict[str, Any]:
    repo_id = str(record.get("repository") or "")
    pattern = str(record.get("pattern") or "unknown")
    target_path = cancellation_target_path(str(record.get("normalizedPath") or record.get("path") or ""))
    route_linked = target_path in async_paths_by_repo.get(repo_id, set())
    operation_target = route_linked or has_async_noun(target_path)
    domain_transition_risk = pattern in STRICT_CANCELLATION_PATTERNS and not operation_target
    return {
        "cancelTargetPath": target_path,
        "routeLevelOperationLinked": route_linked,
        "operationTarget": operation_target,
        "domainTransitionRisk": domain_transition_risk,
        "linkageBucket": linkage_bucket(
            route_linked=route_linked,
            operation_target=operation_target,
            domain_transition_risk=domain_transition_risk,
        ),
    }


def linkage_bucket(
    *,
    route_linked: bool,
    operation_target: bool,
    domain_transition_risk: bool,
) -> str:
    if route_linked:
        return "same-resource-linked"
    if operation_target:
        return "operation-like-target"
    if domain_transition_risk:
        return "domain-transition-risk"
    return "other"


def async_operation_paths_by_repo(
    *,
    evidence: list[dict[str, Any]],
    family_by_repo: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    paths_by_repo: dict[str, set[str]] = defaultdict(set)
    for record in evidence:
        if str(record.get("concept") or "") != "http-async-operation":
            continue
        repo_id = str(record.get("repository") or "")
        if included_family_id(repo_id, family_by_repo) is None:
            continue
        paths_by_repo[repo_id].update(async_resource_paths(record))
    return paths_by_repo


def async_resource_paths(record: dict[str, Any]) -> set[str]:
    path = canonical_path(str(record.get("normalizedPath") or record.get("path") or ""))
    paths = {path}
    segments = path_segments(path)
    if segments and is_status_segment(segments[-1]):
        paths.add(path_from_segments(segments[:-1]))
    method = str(record.get("httpMethod") or "").upper()
    if method == "POST" and has_async_noun(path) and not path.endswith("/{var}"):
        paths.add(path_from_segments([*segments, "{var}"]))
    return paths


def cancellation_target_path(path: str) -> str:
    path = canonical_path(path)
    segments = path_segments(path)
    if segments and is_cancel_action_segment(segments[-1]):
        return path_from_segments(segments[:-1])
    return path


def canonical_path(path: str) -> str:
    value = path.strip()
    if not value:
        return "/"
    if not value.startswith("/"):
        value = f"/{value}"
    if len(value) > 1:
        value = value.rstrip("/")
    return value


def path_segments(path: str) -> list[str]:
    return [segment for segment in canonical_path(path).strip("/").split("/") if segment]


def path_from_segments(segments: list[str]) -> str:
    if not segments:
        return "/"
    return "/" + "/".join(segments)


def is_status_segment(segment: str) -> bool:
    return bool(tokens(segment) & STATUS_WORDS)


def is_cancel_action_segment(segment: str) -> bool:
    return any(part.startswith(prefix) for part in tokens(segment) for prefix in CANCEL_ACTION_PREFIXES)


def included_family_id(repo_id: str, family_by_repo: dict[str, dict[str, Any]]) -> str | None:
    family = family_by_repo.get(repo_id)
    if family and family.get("excluded_from_independent_count"):
        return None
    return str((family or {}).get("family_id") or repo_id)


def new_totals() -> dict[str, Any]:
    return {
        "repositories": set(),
        "families": set(),
        "evidenceCount": 0,
        "routeLevelOperationLinkedRepositories": set(),
        "routeLevelOperationLinkedFamilies": set(),
        "routeLevelOperationLinkedEvidenceCount": 0,
        "operationTargetRepositories": set(),
        "operationTargetFamilies": set(),
        "operationTargetEvidenceCount": 0,
        "domainTransitionRiskRepositories": set(),
        "domainTransitionRiskFamilies": set(),
        "domainTransitionRiskEvidenceCount": 0,
    }


def add_record(
    totals: dict[str, Any],
    repo_id: str,
    family_id: str,
    linkage: dict[str, bool],
) -> None:
    totals["repositories"].add(repo_id)
    totals["families"].add(family_id)
    totals["evidenceCount"] += 1
    if linkage["routeLevelOperationLinked"]:
        totals["routeLevelOperationLinkedRepositories"].add(repo_id)
        totals["routeLevelOperationLinkedFamilies"].add(family_id)
        totals["routeLevelOperationLinkedEvidenceCount"] += 1
    if linkage["operationTarget"]:
        totals["operationTargetRepositories"].add(repo_id)
        totals["operationTargetFamilies"].add(family_id)
        totals["operationTargetEvidenceCount"] += 1
    if linkage["domainTransitionRisk"]:
        totals["domainTransitionRiskRepositories"].add(repo_id)
        totals["domainTransitionRiskFamilies"].add(family_id)
        totals["domainTransitionRiskEvidenceCount"] += 1


def freeze_totals(totals: dict[str, Any]) -> dict[str, int]:
    return {
        "repositoryCount": len(totals["repositories"]),
        "familyCount": len(totals["families"]),
        "evidenceCount": int(totals["evidenceCount"]),
        "routeLevelOperationLinkedRepositoryCount": len(totals["routeLevelOperationLinkedRepositories"]),
        "routeLevelOperationLinkedFamilyCount": len(totals["routeLevelOperationLinkedFamilies"]),
        "routeLevelOperationLinkedEvidenceCount": int(totals["routeLevelOperationLinkedEvidenceCount"]),
        "operationTargetRepositoryCount": len(totals["operationTargetRepositories"]),
        "operationTargetFamilyCount": len(totals["operationTargetFamilies"]),
        "operationTargetEvidenceCount": int(totals["operationTargetEvidenceCount"]),
        "domainTransitionRiskRepositoryCount": len(totals["domainTransitionRiskRepositories"]),
        "domainTransitionRiskFamilyCount": len(totals["domainTransitionRiskFamilies"]),
        "domainTransitionRiskEvidenceCount": int(totals["domainTransitionRiskEvidenceCount"]),
    }


def operation_resource_linked_metrics(
    *,
    strict_totals: dict[str, Any],
    delete_operation_totals: dict[str, Any],
) -> dict[str, int]:
    strict_linked_families = set(strict_totals["routeLevelOperationLinkedFamilies"])
    delete_linked_families = set(delete_operation_totals["routeLevelOperationLinkedFamilies"])
    union_families = strict_linked_families | delete_linked_families
    intersection_families = strict_linked_families & delete_linked_families
    return {
        "strictLinkedFamilyCount": len(strict_linked_families),
        "deleteOperationLinkedFamilyCount": len(delete_linked_families),
        "strictAndDeleteOperationLinkedFamilyCount": len(intersection_families),
        "strictOrDeleteOperationLinkedFamilyCount": len(union_families),
    }
