from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from rfc_miner.clustering import cluster_patterns
from rfc_miner.cli import build_parser
from rfc_miner.collector import clone_or_update, collect_repositories
from rfc_miner.deduplication import dedupe_repositories
from rfc_miner.extractors.openapi import extract_openapi
from rfc_miner.extractors.source_routes import extract_source_routes
from rfc_miner.extraction import analyze_repositories
from rfc_miner.github_discovery import build_queries, seed_from_search_item, should_include_item
from rfc_miner.http_semantics import classify_route
from rfc_miner.io import read_jsonl, write_jsonl
from rfc_miner.io import write_json
from rfc_miner.models import error_record
from rfc_miner.normalization import normalize_evidence, normalize_path, normalize_record
from rfc_miner.paths import data_paths
from rfc_miner.reporting import write_report
from rfc_miner.sampling import (
    stable_evidence_id,
    stable_route_id,
    write_blind_labeling_views,
    write_cancellation_cell_route_sample,
    write_cancellation_family_sample,
    write_cancellation_pilot_sample,
    write_cancellation_route_sample,
    write_cancellation_sample,
)
from rfc_miner.scoring import score_opportunities
from rfc_miner.standards import compare_standards
from rfc_miner.streaming import collect_and_analyze_streaming


class PipelineTests(unittest.TestCase):
    def test_fixture_pipeline_produces_traceable_scores(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            repositories = self.fixture_repositories()
            repository_path = Path(temporary) / "repositories.jsonl"
            write_jsonl(repository_path, repositories)

            evidence, errors = analyze_repositories(paths=paths, repositories_path=repository_path)
            self.assertEqual(errors, [])
            self.assertGreaterEqual(len(evidence), 6)
            self.assertTrue(all(record["file"] and record["lineStart"] for record in evidence))

            normalized = normalize_evidence(paths=paths)
            patterns = {record["pattern"] for record in normalized}
            self.assertIn("post-202-accepted", patterns)
            self.assertIn("post-subresource-cancel", patterns)
            self.assertIn("get-status-resource", patterns)

            families = dedupe_repositories(paths=paths)
            self.assertEqual(len(families), 2)

            clusters = cluster_patterns(paths=paths)
            self.assertIn("http-async-operation", clusters["concepts"])
            self.assertIn("http-cancellation", clusters["concepts"])
            async_metrics = clusters["concepts"]["http-async-operation"]
            self.assertIn("cappedEvidenceCount", async_metrics)
            self.assertIn("dominantRepositoryEvidenceRatio", async_metrics)
            self.assertIn("topEvidenceRepositories", async_metrics)

            compare_standards(
                paths=paths,
                standards_path=ROOT / "config" / "standards" / "http-api-seed.json",
            )
            scores = score_opportunities(paths=paths)
            self.assertGreaterEqual(len(scores["scores"]), 2)
            for score in scores["scores"]:
                self.assertIn("strictScore", score)
                self.assertLessEqual(
                    score["strictIndependentFamilyCount"],
                    score["independentFamilyCount"],
                )

            report = write_report(paths=paths)
            self.assertIn("Top Standardization Opportunities", report)
            self.assertIn("Strict score", report)
            cancellation_candidate = Path(temporary) / "results" / "candidates" / "http-cancellation.md"
            self.assertTrue(cancellation_candidate.exists())
            self.assertIn("Denominator-Safe Ratios", cancellation_candidate.read_text(encoding="utf-8"))
            self.assertTrue((Path(temporary) / "results" / "manual-review.md").exists())

    def test_path_normalization_unifies_common_route_syntaxes(self) -> None:
        self.assertEqual(normalize_path("/jobs/:jobId/cancel"), "/jobs/{var}/cancel")
        self.assertEqual(normalize_path("/jobs/{jobId}/cancel"), "/jobs/{var}/cancel")
        self.assertEqual(normalize_path("/models/{repo_id:path}"), "/models/{var}")
        self.assertEqual(normalize_path("/jobs/<int:job_id>/cancel"), "/jobs/{var}/cancel")

    def test_source_route_extractor_ignores_test_directories(self) -> None:
        repo = self.fixture_repositories()[1]
        evidence = extract_source_routes(repo, str(repo["local_path"]))
        self.assertFalse(any(record["path"] == "/health" for record in evidence))

    def test_source_route_extractor_skips_client_calls_and_test_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "frontend").mkdir()
            (root / "frontend" / "service.ts").write_text("api.delete('/jobs/:id');", encoding="utf-8")
            (root / "chat_test.go").write_text('router.DELETE("/jobs/:id", handler)', encoding="utf-8")
            (root / "routes.ts").write_text("router.delete('/jobs/:id', handler);", encoding="utf-8")
            records = extract_source_routes({"repo_id": "example/service"}, root)
            self.assertEqual([record["file"] for record in records], ["routes.ts"])

    def test_decorator_routes_use_following_handler_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "routes.py").write_text(
                "\n".join(
                    [
                        '@app.put("/jobs/{job_id}/cancel")',
                        "def cancel_job():",
                        "    pass",
                        "",
                        '@app.put("/jobs/{job_id}/retry")',
                        "def retry_job():",
                        "    pass",
                    ]
                ),
                encoding="utf-8",
            )
            records = extract_source_routes({"repo_id": "example/service"}, root)
            self.assertEqual([record["path"] for record in records], ["/jobs/{job_id}/cancel"])
            self.assertEqual(records[0]["symbol"], "cancel_job")

    def test_framework_specific_source_route_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Program.cs").write_text(
                "\n".join(
                    [
                        'app.MapPost("/jobs/{id}/cancel", () => Results.StatusCode(StatusCodes.Status202Accepted));',
                        'var ops = app.MapGroup("/api");',
                        'ops.MapPut("/tasks/{id}", CancelTask);',
                    ]
                ),
                encoding="utf-8",
            )
            (root / "api.php").write_text(
                "\n".join(
                    [
                        "Route::prefix('api')->group(function () {",
                        "    Route::post('tasks/{id}/cancel', [TaskController::class, 'cancel']);",
                        "    Route::delete('/tasks/{id}', [TaskController::class, 'cancel']);",
                        "});",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "router.ex").write_text(
                'scope "/api", MyAppWeb do\n  post "/runs/:id/cancel", RunController, :cancel\nend\n',
                encoding="utf-8",
            )
            records = extract_source_routes({"repo_id": "example/service"}, root)
            extracted = {
                (
                    record["extractedValue"]["routePattern"],
                    record["httpMethod"],
                    record["path"],
                    record["concept"],
                )
                for record in records
            }
            self.assertIn(
                ("aspnet-map-method", "POST", "/jobs/{id}/cancel", "http-cancellation"),
                extracted,
            )
            self.assertIn(
                ("aspnet-map-method", "POST", "/jobs/{id}/cancel", "http-async-operation"),
                extracted,
            )
            self.assertIn(
                ("aspnet-map-method", "PUT", "/api/tasks/{id}", "http-cancellation"),
                extracted,
            )
            self.assertIn(
                ("laravel-route", "POST", "/api/tasks/{id}/cancel", "http-cancellation"),
                extracted,
            )
            self.assertIn(
                ("laravel-route", "DELETE", "/api/tasks/{id}", "http-cancellation"),
                extracted,
            )
            self.assertIn(
                ("phoenix-route", "POST", "/api/runs/:id/cancel", "http-cancellation"),
                extracted,
            )

            with tempfile.TemporaryDirectory() as other_temporary:
                other_root = Path(other_temporary)
                (other_root / "client.ex").write_text('post "/runs/:id/cancel", body\n', encoding="utf-8")
                self.assertEqual(extract_source_routes({"repo_id": "example/client"}, other_root), [])

    def test_extractors_skip_unreadable_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locked = root / "locked"
            locked.mkdir()
            (root / "routes.ts").write_text("app.post('/jobs', createJob);", encoding="utf-8")
            repo = {"repo_id": "example/service", "commit_hash": "abc123"}
            try:
                locked.chmod(0)
                source_evidence = extract_source_routes(repo, root)
                openapi_evidence = extract_openapi(repo, root)
            finally:
                locked.chmod(0o700)
            self.assertIsInstance(source_evidence, list)
            self.assertIsInstance(openapi_evidence, list)

    def test_openapi_extractor_preserves_operation_summary_and_description(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "openapi.json").write_text(
                json.dumps(
                    {
                        "openapi": "3.1.0",
                        "paths": {
                            "/jobs/{id}/cancel": {
                                "post": {
                                    "operationId": "cancelJob",
                                    "summary": "Cancel a running job",
                                    "description": "Requests cancellation while the job is queued or running.",
                                    "responses": {"202": {"description": "Accepted"}},
                                }
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            rows = extract_openapi({"repo_id": "example/api", "commit_hash": "abc123"}, root)
            cancellation_row = next(row for row in rows if row["concept"] == "http-cancellation")
            self.assertEqual(cancellation_row["extractedValue"]["summary"], "Cancel a running job")
            self.assertEqual(
                cancellation_row["extractedValue"]["description"],
                "Requests cancellation while the job is queued or running.",
            )

    def test_cancellation_requires_strong_cancel_evidence(self) -> None:
        false_positive = classify_route(
            method="GET",
            path="/stacktrace",
            operation_text="request context can be cancelled by clients",
        )
        self.assertEqual(false_positive, [])

        adjacent_symbol = classify_route(
            method="PUT",
            path="/:id/file",
            operation_text="/:id/file abort workflow context",
            operation_name="abort",
        )
        self.assertEqual(adjacent_symbol, [])

        stop_route = classify_route(
            method="PUT",
            path="/api/v1/workflows/{namespace}/{name}/stop",
            operation_name="WorkflowService_StopWorkflow",
        )
        self.assertTrue(any(record["concept"] == "http-cancellation" for record in stop_route))

        export_cancel = classify_route(
            method="POST",
            path="/exports/{id}/cancel",
            operation_name="cancelExport",
        )
        self.assertTrue(any(record["concept"] == "http-cancellation" for record in export_cancel))

        normalized = normalize_record(
            {
                "concept": "http-cancellation",
                "httpMethod": "PUT",
                "path": "/api/v1/workflows/{namespace}/{name}/stop",
                "responseCodes": [],
                "symbol": "WorkflowService_StopWorkflow",
                "extractedValue": {},
            }
        )
        self.assertEqual(normalized["pattern"], "put-action-cancel")

        kill_switch = normalize_record(
            {
                "concept": "http-cancellation",
                "httpMethod": "PUT",
                "path": "/controls/kill-switches",
                "responseCodes": [],
                "symbol": "updateKillSwitches",
                "extractedValue": {},
            }
        )
        self.assertEqual(kill_switch["pattern"], "put-action-cancel")

        cancel_plan = normalize_record(
            {
                "concept": "http-cancellation",
                "httpMethod": "GET",
                "path": "/billing/cancel-plan",
                "responseCodes": [200],
                "symbol": "getBillingCancelPlan",
                "extractedValue": {},
            }
        )
        self.assertEqual(cancel_plan["pattern"], "get-cancel-link")

        put_name_based = normalize_record(
            {
                "concept": "http-cancellation",
                "httpMethod": "PUT",
                "path": "/tasks/{id}",
                "responseCodes": [],
                "symbol": "CancelTask",
                "extractedValue": {},
            }
        )
        self.assertEqual(put_name_based["pattern"], "put-action-cancel")

        delete_name_based = normalize_record(
            {
                "concept": "http-cancellation",
                "httpMethod": "DELETE",
                "path": "/tasks/{id}",
                "responseCodes": [],
                "symbol": "cancel",
                "extractedValue": {},
            }
        )
        self.assertEqual(delete_name_based["pattern"], "delete-action-cancel")

    def test_normalization_deduplicates_repository_source_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            write_jsonl(
                paths.raw_evidence,
                [
                    {
                        "repository": "example/service",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs",
                        "responseCodes": [],
                        "file": "openapi-v1.yaml",
                        "symbol": "createJob",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.6,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/service",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs",
                        "responseCodes": [202],
                        "file": "openapi-v2.yaml",
                        "symbol": "createJob",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.5,
                        "extractedValue": {},
                        "extractor": "openapi-yaml-lite",
                    },
                    {
                        "repository": "example/service",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs",
                        "responseCodes": [202],
                        "file": "routes.py",
                        "symbol": "create_job",
                        "lineStart": 3,
                        "lineEnd": 3,
                        "confidence": 0.7,
                        "extractedValue": {},
                        "extractor": "source-routes",
                    },
                ],
            )

            normalized = normalize_evidence(paths=paths)
            self.assertEqual(len(normalized), 2)
            openapi_record = next(record for record in normalized if record["sourceKind"] == "openapi")
            source_record = next(record for record in normalized if record["sourceKind"] == "source")
            self.assertEqual(openapi_record["responseCodes"], [202])
            self.assertEqual(openapi_record["pattern"], "post-202-accepted")
            self.assertEqual(openapi_record["duplicateEvidenceCount"], 2)
            self.assertEqual(source_record["pattern"], "post-202-accepted")

    def test_cancellation_linkage_requires_same_operation_resource(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            write_jsonl(
                paths.repositories,
                [
                    {"repo_id": "example/ops", "repository_url": "https://github.com/example/ops"},
                    {
                        "repo_id": "example/domain",
                        "repository_url": "https://github.com/example/domain",
                    },
                ],
            )
            write_jsonl(
                paths.raw_evidence,
                [
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "GET",
                        "path": "/jobs/{id}/status",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.9,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs/{id}/cancel",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.96,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "DELETE",
                        "path": "/jobs/{id}",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 3,
                        "lineEnd": 3,
                        "confidence": 0.64,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/domain",
                        "commit": "def456",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "GET",
                        "path": "/jobs/{id}/status",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.9,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/domain",
                        "commit": "def456",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/subscriptions/{id}/cancel",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.78,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                ],
            )

            normalize_evidence(paths=paths)
            dedupe_repositories(paths=paths)
            clusters = cluster_patterns(paths=paths)
            linkage = clusters["concepts"]["http-cancellation"]["operationLinkage"]["strict"]
            operation_resource = clusters["concepts"]["http-cancellation"]["operationLinkage"][
                "operationResourceLinked"
            ]

            self.assertEqual(linkage["familyCount"], 2)
            self.assertEqual(linkage["routeLevelOperationLinkedFamilyCount"], 1)
            self.assertEqual(linkage["operationTargetFamilyCount"], 1)
            self.assertEqual(linkage["domainTransitionRiskFamilyCount"], 1)
            self.assertEqual(operation_resource["strictLinkedFamilyCount"], 1)
            self.assertEqual(operation_resource["deleteOperationLinkedFamilyCount"], 1)
            self.assertEqual(operation_resource["strictAndDeleteOperationLinkedFamilyCount"], 1)
            self.assertEqual(operation_resource["strictOrDeleteOperationLinkedFamilyCount"], 1)

    def test_cancellation_sample_sheet_uses_linkage_buckets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            write_jsonl(
                paths.repositories,
                [
                    {"repo_id": "example/ops", "repository_url": "https://github.com/example/ops"},
                    {
                        "repo_id": "example/domain",
                        "repository_url": "https://github.com/example/domain",
                    },
                ],
            )
            write_jsonl(
                paths.raw_evidence,
                [
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "GET",
                        "path": "/jobs/{id}/status",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.9,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs/{id}/cancel",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.96,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/subscriptions/{id}/cancel",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 3,
                        "lineEnd": 3,
                        "confidence": 0.78,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/domain",
                        "commit": "def456",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/subscriptions/{id}/cancel",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.78,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                ],
            )
            normalize_evidence(paths=paths)
            dedupe_repositories(paths=paths)

            output, count = write_cancellation_sample(paths=paths, profile="minimum", seed=1)
            with output.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(count, 2)
            self.assertEqual(len({(row["family_id"], row["pattern"]) for row in rows}), len(rows))
            self.assertEqual({row["primaryLabel"] for row in rows}, {""})
            self.assertEqual({row["samplingUnit"] for row in rows}, {"family-pattern-representative"})
            self.assertEqual({row["estimationPopulation"] for row in rows}, {"strict-cancellation"})
            self.assertEqual({row["populationFamilyMemberships"] for row in rows}, {"2"})
            self.assertTrue(all(row["route_id"] for row in rows))
            self.assertTrue(all(row["evidence_id"] for row in rows))
            self.assertTrue(all(row["cellRouteCount"] for row in rows))
            self.assertTrue(all(row["familyPatternCancellationEvidence"] for row in rows))
            self.assertTrue(all(row["strictFamilyApproxInclusionProbability"] for row in rows))
            self.assertEqual(
                {row["linkageBucket"] for row in rows},
                {"mixed-same-resource-and-risk", "domain-transition-risk"},
            )
            domain_row = next(row for row in rows if row["repository"] == "example/domain")
            self.assertEqual(domain_row["cancelTargetPath"], "/subscriptions/{var}")
            self.assertEqual(domain_row["domainTransitionRisk"], "true")
            summary = json.loads(output.with_suffix(".summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["estimationGuidance"]["doNotPoolRawRows"])
            self.assertEqual(summary["samplingUnit"], "family-pattern-representative")

            route_output, route_count = write_cancellation_route_sample(paths=paths, profile="minimum", seed=1)
            with route_output.open("r", encoding="utf-8", newline="") as handle:
                route_rows = list(csv.DictReader(handle))

            self.assertEqual(route_count, 3)
            self.assertEqual({row["samplingUnit"] for row in route_rows}, {"route-record"})
            self.assertEqual({row["estimationPopulation"] for row in route_rows}, {"route-cancellation-record"})
            self.assertEqual(
                {row["routeStratum"] for row in route_rows},
                {"post-subresource-cancel:linked", "post-subresource-cancel:unlinked"},
            )
            route_summary = json.loads(route_output.with_suffix(".summary.json").read_text(encoding="utf-8"))
            self.assertEqual(route_summary["samplingUnit"], "route-record")
            self.assertIn("blindLabeling", route_summary["estimationGuidance"])

            cell_route_output, cell_route_count = write_cancellation_cell_route_sample(
                paths=paths,
                profile="minimum",
                seed=1,
            )
            with cell_route_output.open("r", encoding="utf-8", newline="") as handle:
                cell_route_rows = list(csv.DictReader(handle))

            self.assertEqual(cell_route_count, 3)
            self.assertEqual({row["samplingUnit"] for row in cell_route_rows}, {"family-pattern-cell-route"})
            self.assertEqual(
                {row["normalizedPath"] for row in cell_route_rows},
                {"/jobs/{var}/cancel", "/subscriptions/{var}/cancel"},
            )
            self.assertEqual(len({row["cell_sample_id"] for row in cell_route_rows}), 2)
            cell_route_summary = json.loads(
                cell_route_output.with_suffix(".summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue(cell_route_summary["estimationGuidance"]["doNotUseAsRouteFrame"])

            labeling_output, machine_output, split_count = write_blind_labeling_views(
                input_path=cell_route_output,
                labeling_output_path=Path(temporary) / "labeling.csv",
                machine_output_path=Path(temporary) / "machine.csv",
            )
            with labeling_output.open("r", encoding="utf-8", newline="") as handle:
                labeling_rows = list(csv.DictReader(handle))
            with labeling_output.open("r", encoding="utf-8", newline="") as handle:
                labeling_reader = csv.DictReader(handle)
                list(labeling_reader)
                labeling_fields = set(labeling_reader.fieldnames or [])
            with machine_output.open("r", encoding="utf-8", newline="") as handle:
                machine_reader = csv.DictReader(handle)
                machine_rows = list(machine_reader)
                machine_fields = set(machine_reader.fieldnames or [])

            self.assertEqual(split_count, cell_route_count)
            self.assertEqual(len(labeling_rows), cell_route_count)
            self.assertEqual(len(machine_rows), cell_route_count)
            self.assertNotIn("routeLevelOperationLinked", labeling_fields)
            self.assertNotIn("operationTarget", labeling_fields)
            self.assertNotIn("domainTransitionRisk", labeling_fields)
            self.assertNotIn("confidence", labeling_fields)
            self.assertNotIn("unanchored_subset", labeling_fields)
            self.assertNotIn("draft_visible_to_human", labeling_fields)
            self.assertIn("labelerA_label", labeling_fields)
            self.assertIn("labelerA_rationale", labeling_fields)
            self.assertIn("labelerA_confidence", labeling_fields)
            self.assertIn("labelerB_label", labeling_fields)
            self.assertIn("labelerB_rationale", labeling_fields)
            self.assertIn("labelerB_confidence", labeling_fields)
            self.assertIn("agreement", labeling_fields)
            self.assertIn("final_label", labeling_fields)
            self.assertIn("adjudicated", labeling_fields)
            self.assertIn("adjudicator_rationale", labeling_fields)
            self.assertIn("routeLevelOperationLinked", machine_fields)
            self.assertIn("evidence_id", labeling_fields)
            self.assertIn("evidence_id", machine_fields)
            self.assertTrue(
                all(
                    row[column] == ""
                    for row in labeling_rows
                    for column in {
                        "labelerA_label",
                        "labelerA_rationale",
                        "labelerA_confidence",
                        "labelerB_label",
                        "labelerB_rationale",
                        "labelerB_confidence",
                        "agreement",
                        "final_label",
                        "adjudicated",
                        "adjudicator_rationale",
                    }
                )
            )
            labeling_summary = json.loads(
                labeling_output.with_suffix(".summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue(labeling_summary["workflow"]["unanchoredSubsetRemoved"])
            self.assertEqual(labeling_summary["labelingProvenance"]["labelingTemperature"], 0)
            self.assertIn("DELETE taxonomy label", labeling_summary["workflow"]["agreementDefinition"])

    def test_blind_labeling_view_adds_openapi_operation_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            record = {
                "repository": "example/api",
                "commit": "abc123",
                "concept": "http-cancellation",
                "evidenceType": "openapi_operation",
                "httpMethod": "POST",
                "normalizedPath": "/jobs/{var}/cancel",
                "path": "/jobs/{id}/cancel",
                "sourceKind": "openapi",
                "pattern": "post-subresource-cancel",
                "file": "openapi.json",
                "lineStart": 10,
                "symbol": "cancelJob",
                "responseCodes": [202],
                "confidence": 0.98,
                "extractedValue": {
                    "operationId": "cancelJob",
                    "summary": "Cancel a running job",
                    "description": "Requests cancellation while the job is queued or running.",
                },
            }
            write_jsonl(paths.normalized_evidence, [record])
            route_id = stable_route_id(record)
            evidence_id = stable_evidence_id(record, route_id=route_id)
            input_path = Path(temporary) / "cell-routes.csv"
            with input_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "sample_id",
                        "cell_sample_id",
                        "cellRouteOrdinal",
                        "route_id",
                        "evidence_id",
                        "repository",
                        "commit",
                        "httpMethod",
                        "normalizedPath",
                        "path",
                        "sourceKind",
                        "file",
                        "lineStart",
                        "symbol",
                        "responseCodes",
                        "pattern",
                    ],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "sample_id": "row-1",
                        "cell_sample_id": "cell-1",
                        "cellRouteOrdinal": "1",
                        "route_id": route_id,
                        "evidence_id": evidence_id,
                        "repository": "example/api",
                        "commit": "abc123",
                        "httpMethod": "POST",
                        "normalizedPath": "/jobs/{var}/cancel",
                        "path": "/jobs/{id}/cancel",
                        "sourceKind": "openapi",
                        "file": "openapi.json",
                        "lineStart": "10",
                        "symbol": "cancelJob",
                        "responseCodes": "202",
                        "pattern": "post-subresource-cancel",
                    }
                )

            labeling_output, _, _ = write_blind_labeling_views(
                input_path=input_path,
                labeling_output_path=Path(temporary) / "labeling.csv",
                machine_output_path=Path(temporary) / "machine.csv",
                paths=paths,
            )
            with labeling_output.open("r", encoding="utf-8", newline="") as handle:
                labeling_rows = list(csv.DictReader(handle))
            self.assertEqual(labeling_rows[0]["operationSummary"], "Cancel a running job")
            self.assertEqual(
                labeling_rows[0]["operationDescription"],
                "Requests cancellation while the job is queued or running.",
            )

    def test_cancellation_pilot_sample_uses_blinded_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            labeling_path = Path(temporary) / "labeling.csv"
            machine_path = Path(temporary) / "machine.csv"
            labeling_fields = [
                "sample_id",
                "httpMethod",
                "normalizedPath",
                "path",
                "responseCodes",
                "sourceKind",
                "file",
                "symbol",
                "operationSummary",
                "operationDescription",
            ]
            machine_fields = ["sample_id", "evidence_id", "pattern"]
            with labeling_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=labeling_fields + ["evidence_id"], lineterminator="\n")
                writer.writeheader()
                for index in range(25):
                    method = "DELETE" if index % 2 == 0 else "POST"
                    for prefix in ("delete", "post"):
                        writer.writerow(
                            {
                                "sample_id": f"{prefix}-{index:03d}",
                                "evidence_id": f"{prefix}-evidence-{index:03d}",
                                "httpMethod": method if prefix == "delete" else "POST",
                                "normalizedPath": f"/jobs/{index}",
                                "path": f"/jobs/{index}",
                                "responseCodes": "202",
                                "sourceKind": "openapi",
                                "file": "openapi.json",
                                "symbol": "",
                                "operationSummary": "Visible summary",
                                "operationDescription": "",
                            }
                        )
            with machine_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=machine_fields, lineterminator="\n")
                writer.writeheader()
                for index in range(25):
                    writer.writerow(
                        {
                            "sample_id": f"delete-{index:03d}",
                            "evidence_id": f"delete-evidence-{index:03d}",
                            "pattern": "delete-operation-resource",
                        }
                    )
                    writer.writerow(
                        {
                            "sample_id": f"post-{index:03d}",
                            "evidence_id": f"post-evidence-{index:03d}",
                            "pattern": "post-subresource-cancel",
                        }
                    )

            output_path, count = write_cancellation_pilot_sample(
                labeling_input_path=labeling_path,
                machine_input_path=machine_path,
                output_path=Path(temporary) / "pilot.csv",
                seed=1,
            )
            with output_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                pilot_rows = list(reader)
                pilot_fields = reader.fieldnames or []
            summary = json.loads(output_path.with_suffix(".summary.json").read_text(encoding="utf-8"))

            self.assertEqual(count, 40)
            self.assertEqual(len(pilot_rows), 40)
            self.assertEqual(pilot_fields, [
                "sample_id",
                "httpMethod",
                "normalizedPath",
                "path",
                "responseCodes",
                "sourceKind",
                "file",
                "symbol",
                "operationSummary",
                "operationDescription",
            ])
            self.assertNotIn("pattern", pilot_fields)
            self.assertEqual(summary["byPattern"], {
                "delete-operation-resource": 20,
                "post-subresource-cancel": 20,
            })

    def test_labeling_prompts_are_blind_to_detection_patterns(self) -> None:
        forbidden_patterns = {
            "post-subresource-cancel",
            "post-action-cancel",
            "delete-action-cancel",
            "put-action-cancel",
            "get-cancel-link",
            "patch-state-cancelled",
        }
        for prompt in (ROOT / "prompts" / "label-a.md", ROOT / "prompts" / "label-b.md"):
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("operation-cancellation", text)
            self.assertIn("domain-state-transition", text)
            self.assertIn("deletion-or-archival", text)
            self.assertIn("ambiguous", text)
            for pattern in forbidden_patterns:
                self.assertNotIn(pattern, text)

    def test_cancellation_representative_route_is_seeded_not_outcome_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            write_jsonl(
                paths.repositories,
                [{"repo_id": "example/ops", "repository_url": "https://github.com/example/ops"}],
            )
            write_jsonl(
                paths.raw_evidence,
                [
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "GET",
                        "path": "/jobs/{id}/status",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.9,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs/{id}/cancel",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.96,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/subscriptions/{id}/cancel",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 3,
                        "lineEnd": 3,
                        "confidence": 0.78,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                ],
            )
            normalize_evidence(paths=paths)
            dedupe_repositories(paths=paths)

            first_output, first_count = write_cancellation_sample(
                paths=paths,
                output_path=Path(temporary) / "first.csv",
                profile="minimum",
                seed=1,
            )
            second_output, second_count = write_cancellation_sample(
                paths=paths,
                output_path=Path(temporary) / "second.csv",
                profile="minimum",
                seed=2,
            )
            repeat_output, repeat_count = write_cancellation_sample(
                paths=paths,
                output_path=Path(temporary) / "repeat.csv",
                profile="minimum",
                seed=1,
            )
            with first_output.open("r", encoding="utf-8", newline="") as handle:
                first_rows = list(csv.DictReader(handle))
            with second_output.open("r", encoding="utf-8", newline="") as handle:
                second_rows = list(csv.DictReader(handle))

            self.assertEqual(first_count, 1)
            self.assertEqual(second_count, 1)
            self.assertEqual(repeat_count, first_count)
            self.assertEqual(repeat_output.read_text(encoding="utf-8"), first_output.read_text(encoding="utf-8"))
            self.assertEqual(first_rows[0]["normalizedPath"], "/subscriptions/{var}/cancel")
            self.assertEqual(first_rows[0]["routeLevelOperationLinked"], "false")
            self.assertEqual(second_rows[0]["normalizedPath"], "/jobs/{var}/cancel")
            self.assertEqual(second_rows[0]["routeLevelOperationLinked"], "true")
            self.assertEqual(len(first_rows[0]["route_id"]), 64)
            self.assertEqual(len(first_rows[0]["evidence_id"]), 64)

    def test_cancellation_ids_separate_route_identity_from_evidence_identity(self) -> None:
        base_record = {
            "repository": "example/ops",
            "commit": "abc123",
            "pattern": "post-subresource-cancel",
            "httpMethod": "POST",
            "normalizedPath": "/jobs/{var}/cancel",
            "path": "/jobs/{id}/cancel",
            "sourceKind": "source",
            "file": "routes.py",
            "lineStart": 10,
            "symbol": "cancel_job",
        }
        changed_commit = dict(base_record, commit="def456")
        changed_source = dict(base_record, sourceKind="openapi", file="openapi.yaml")

        self.assertEqual(stable_route_id(base_record), stable_route_id(changed_commit))
        self.assertEqual(stable_route_id(base_record), stable_route_id(changed_source))
        self.assertNotEqual(
            stable_evidence_id(base_record, route_id=stable_route_id(base_record)),
            stable_evidence_id(changed_commit, route_id=stable_route_id(changed_commit)),
        )
        self.assertNotEqual(
            stable_evidence_id(base_record, route_id=stable_route_id(base_record)),
            stable_evidence_id(changed_source, route_id=stable_route_id(changed_source)),
        )

    def test_primary_pattern_removes_cross_pattern_route_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            write_jsonl(
                paths.repositories,
                [{"repo_id": "example/ops", "repository_url": "https://github.com/example/ops"}],
            )
            write_jsonl(
                paths.raw_evidence,
                [
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "GET",
                        "path": "/jobs/{id}",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.9,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "DELETE",
                        "path": "/jobs/{id}",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "symbol": "cancelJob",
                        "confidence": 0.8,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "DELETE",
                        "path": "/jobs/{id}",
                        "responseCodes": [202],
                        "file": "routes.py",
                        "lineStart": 3,
                        "lineEnd": 3,
                        "symbol": "",
                        "confidence": 0.6,
                        "extractedValue": {},
                        "extractor": "source-routes",
                    },
                ],
            )
            normalize_evidence(paths=paths)
            dedupe_repositories(paths=paths)

            output, count = write_cancellation_cell_route_sample(paths=paths, profile="minimum", seed=1)
            with output.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(count, 1)
            self.assertEqual(rows[0]["pattern"], "delete-action-cancel")
            self.assertEqual(len({row["route_id"] for row in rows}), 1)
            self.assertEqual({row["pattern"] for row in rows}, {"delete-action-cancel"})

    def test_cancellation_family_sample_uses_unique_families(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(temporary)
            write_jsonl(
                paths.repositories,
                [
                    {"repo_id": "example/ops", "repository_url": "https://github.com/example/ops"},
                    {
                        "repo_id": "example/domain",
                        "repository_url": "https://github.com/example/domain",
                    },
                ],
            )
            write_jsonl(
                paths.raw_evidence,
                [
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-async-operation",
                        "evidenceType": "route",
                        "httpMethod": "GET",
                        "path": "/jobs/{id}/status",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 1,
                        "lineEnd": 1,
                        "confidence": 0.9,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/jobs/{id}/cancel",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.96,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/ops",
                        "commit": "abc123",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "PUT",
                        "path": "/jobs/{id}/cancel",
                        "responseCodes": [202],
                        "file": "openapi.yaml",
                        "lineStart": 3,
                        "lineEnd": 3,
                        "confidence": 0.88,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                    {
                        "repository": "example/domain",
                        "commit": "def456",
                        "concept": "http-cancellation",
                        "evidenceType": "route",
                        "httpMethod": "POST",
                        "path": "/subscriptions/{id}/cancel",
                        "responseCodes": [200],
                        "file": "openapi.yaml",
                        "lineStart": 2,
                        "lineEnd": 2,
                        "confidence": 0.78,
                        "extractedValue": {},
                        "extractor": "openapi",
                    },
                ],
            )
            normalize_evidence(paths=paths)
            dedupe_repositories(paths=paths)

            output, count = write_cancellation_family_sample(paths=paths, profile="minimum", seed=1)
            with output.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(count, 2)
            self.assertEqual(len({row["family_id"] for row in rows}), len(rows))
            self.assertEqual({row["samplingUnit"] for row in rows}, {"strict-cancellation-family"})
            self.assertEqual({row["estimationPopulation"] for row in rows}, {"strict-cancellation-family"})
            self.assertEqual({row["populationStrictFamilies"] for row in rows}, {"2"})
            ops_row = next(row for row in rows if row["repository"] == "example/ops")
            self.assertEqual(ops_row["strictFamilyPatternMemberships"], "post-subresource-cancel,put-action-cancel")
            self.assertTrue(ops_row["strictFamilyCancellationEvidence"])
            summary = json.loads(output.with_suffix(".summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["samplingUnit"], "strict-cancellation-family")
            self.assertEqual(summary["populationStrictFamilies"], 2)

    def test_collect_records_clone_errors_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(Path(temporary) / "data")
            seed_path = Path(temporary) / "seed.json"
            write_json(
                seed_path,
                {
                    "repositories": [
                        {
                            "repository_url": "https://github.com/example/missing",
                            "owner": "example",
                            "name": "missing",
                        }
                    ]
                },
            )
            with patch("rfc_miner.collector.fetch_github_metadata", return_value={}), patch(
                "rfc_miner.collector.clone_or_update",
                side_effect=subprocess.CalledProcessError(
                    128,
                    ["git", "clone"],
                    stderr="repository not found",
                ),
            ):
                repositories = collect_repositories(
                    seed_path=seed_path,
                    paths=paths,
                    repo_dir=Path(temporary) / "repos",
                )
            self.assertEqual(len(repositories), 1)
            self.assertIsNone(repositories[0]["local_path"])
            errors = read_jsonl(paths.errors)
            self.assertEqual(errors[0]["errorType"], "git_clone_failed")

    def test_clone_uses_shallow_single_branch_without_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "repo"
            with patch("rfc_miner.collector.subprocess.run") as run:
                clone_or_update("https://github.com/example/service", destination)
            command = run.call_args.args[0]
            self.assertIn("--depth", command)
            self.assertIn("--single-branch", command)
            self.assertIn("--no-tags", command)

    def test_streaming_run_resumes_without_duplicate_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(Path(temporary) / "data")
            seed_path = Path(temporary) / "seed.json"
            repositories = self.fixture_repositories()
            write_json(seed_path, {"repositories": repositories})

            collect_and_analyze_streaming(
                seed_path=seed_path,
                paths=paths,
                repo_dir=Path(temporary) / "repos",
                limit=1,
                progress=False,
            )
            collect_and_analyze_streaming(
                seed_path=seed_path,
                paths=paths,
                repo_dir=Path(temporary) / "repos",
                limit=2,
                progress=False,
                jobs=2,
            )
            collect_and_analyze_streaming(
                seed_path=seed_path,
                paths=paths,
                repo_dir=Path(temporary) / "repos",
                limit=2,
                progress=False,
                jobs=2,
            )

            self.assertEqual(len(read_jsonl(paths.repositories)), 2)
            repo_ids = [record["repo_id"] for record in read_jsonl(paths.repositories)]
            self.assertEqual(sorted(repo_ids), sorted({repo["repo_id"] for repo in repositories}))

    def test_streaming_resume_retries_retryable_repository_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = data_paths(Path(temporary) / "data")
            seed_path = Path(temporary) / "seed.json"
            seed = {
                "repository_url": "https://github.com/example/service",
                "owner": "example",
                "name": "service",
            }
            write_json(seed_path, {"repositories": [seed]})
            attempts = []

            def fake_collect(item: dict[str, object], repo_root: Path, keep_repos: bool) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
                attempts.append(item)
                if len(attempts) == 1:
                    return (
                        {"repo_id": "example/service", "repository_url": seed["repository_url"]},
                        [],
                        [
                            error_record(
                                repo="example/service",
                                stage="collect",
                                error_type="git_clone_failed",
                                error="temporary network failure",
                                retryable=True,
                            )
                        ],
                    )
                return (
                    {"repo_id": "example/service", "repository_url": seed["repository_url"]},
                    [],
                    [],
                )

            with patch("rfc_miner.streaming.collect_analyze_one", side_effect=fake_collect):
                collect_and_analyze_streaming(
                    seed_path=seed_path,
                    paths=paths,
                    repo_dir=Path(temporary) / "repos",
                    progress=False,
                )
                collect_and_analyze_streaming(
                    seed_path=seed_path,
                    paths=paths,
                    repo_dir=Path(temporary) / "repos",
                    progress=False,
                )

            self.assertEqual(len(attempts), 2)
            self.assertEqual(len(read_jsonl(paths.repositories)), 1)
            self.assertEqual(read_jsonl(paths.errors), [])

    def test_cli_run_on_fixture_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository_path = Path(temporary) / "repositories.jsonl"
            write_jsonl(repository_path, self.fixture_repositories())
            env = dict(os.environ)
            env["PYTHONPATH"] = str(SRC)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rfc_miner.cli",
                    "run",
                    "--skip-collect",
                    "--repositories",
                    str(repository_path),
                    "--data-dir",
                    str(Path(temporary) / "data"),
                    "--standards",
                    str(ROOT / "config" / "standards" / "http-api-seed.json"),
                ],
                cwd=ROOT,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertIn("report:", result.stdout)
            report = Path(temporary) / "data" / "results" / "report.md"
            self.assertTrue(report.exists())

    def test_cli_uses_storage_environment_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RFC_MINER_DATA_DIR": "/tmp/rfc-miner-data",
                "RFC_MINER_REPO_DIR": "/tmp/rfc-miner-repos",
            },
        ):
            args = build_parser().parse_args(["run"])
        self.assertEqual(args.data_dir, "/tmp/rfc-miner-data")
        self.assertEqual(args.repo_dir, "/tmp/rfc-miner-repos")

    def test_github_discovery_builds_seed_records(self) -> None:
        queries = build_queries(
            languages=["Go"],
            terms=["openapi"],
            min_stars=20,
            updated_since="2024-01-01",
        )
        self.assertEqual(
            queries[0],
            "openapi language:Go stars:>=20 pushed:>=2024-01-01 size:<250000 archived:false fork:false",
        )
        self.assertEqual(
            build_queries(
                languages=["Go", "Python"],
                terms=["workflow", "scheduler"],
                min_stars=20,
                updated_since="2024-01-01",
            )[:4],
            [
                "workflow language:Go stars:>=20 pushed:>=2024-01-01 size:<250000 archived:false fork:false",
                "workflow language:Python stars:>=20 pushed:>=2024-01-01 size:<250000 archived:false fork:false",
                "scheduler language:Go stars:>=20 pushed:>=2024-01-01 size:<250000 archived:false fork:false",
                "scheduler language:Python stars:>=20 pushed:>=2024-01-01 size:<250000 archived:false fork:false",
            ],
        )

        seed = seed_from_search_item(
            {
                "html_url": "https://github.com/example/api-server",
                "owner": {"login": "example"},
                "name": "api-server",
                "full_name": "example/api-server",
                "language": "Go",
                "stargazers_count": 123,
                "forks_count": 4,
                "license": {"spdx_id": "Apache-2.0"},
                "pushed_at": "2026-09-04T00:00:00Z",
                "default_branch": "main",
                "description": "OpenAPI workflow server",
                "topics": ["openapi", "workflow"],
            }
        )
        self.assertIsNotNone(seed)
        assert seed is not None
        self.assertEqual(seed["repository_url"], "https://github.com/example/api-server")
        self.assertEqual(seed["project_category"], "workflow-engine")

    def test_github_discovery_excludes_sdk_only_candidates(self) -> None:
        excluded_items = [
            {
                "html_url": "https://github.com/example/api-client-go",
                "owner": {"login": "example"},
                "name": "api-client-go",
                "description": "Generated OpenAPI API client SDK",
                "topics": ["openapi", "sdk"],
            },
            {
                "html_url": "https://github.com/example/awesome-workflows",
                "owner": {"login": "example"},
                "name": "awesome-workflows",
                "description": "Curated workflow links",
                "topics": ["workflow"],
            },
            {
                "html_url": "https://github.com/example/setup-thing",
                "owner": {"login": "example"},
                "name": "setup-thing",
                "description": "GitHub Action for workflows",
                "topics": ["github-action"],
            },
            {
                "html_url": "https://github.com/example/agent-flow",
                "owner": {"login": "example"},
                "name": "agent-flow",
                "description": "Reusable prompt workflow collection",
                "topics": ["workflow"],
            },
            {
                "html_url": "https://github.com/example/large-api-server",
                "owner": {"login": "example"},
                "name": "large-api-server",
                "description": "Workflow API server",
                "topics": ["workflow", "api"],
                "size": 300_000,
            },
        ]
        for item in excluded_items:
            self.assertFalse(should_include_item(item))
        self.assertTrue(
            should_include_item(
                {
                    "html_url": "https://github.com/example/workflow-server",
                    "owner": {"login": "example"},
                    "name": "workflow-server",
                    "description": "Workflow orchestration API server",
                    "topics": ["workflow", "api"],
                }
            )
        )

    def fixture_repositories(self) -> list[dict[str, object]]:
        raw = read_jsonl(ROOT / "tests" / "fixtures" / "data" / "raw" / "repositories.jsonl")
        repositories = []
        for record in raw:
            updated = dict(record)
            updated["local_path"] = str(ROOT / str(record["local_path"]))
            repositories.append(updated)
        return repositories


if __name__ == "__main__":
    unittest.main()
