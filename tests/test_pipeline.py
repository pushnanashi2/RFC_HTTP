from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
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

            report = write_report(paths=paths)
            self.assertIn("Top Standardization Opportunities", report)
            self.assertTrue((Path(temporary) / "results" / "candidates" / "http-cancellation.md").exists())
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
