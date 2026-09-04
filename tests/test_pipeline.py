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
from rfc_miner.collector import collect_repositories
from rfc_miner.deduplication import dedupe_repositories
from rfc_miner.extractors.source_routes import extract_source_routes
from rfc_miner.extraction import analyze_repositories
from rfc_miner.http_semantics import classify_route
from rfc_miner.io import read_jsonl, write_jsonl
from rfc_miner.io import write_json
from rfc_miner.normalization import normalize_evidence, normalize_path, normalize_record
from rfc_miner.paths import data_paths
from rfc_miner.reporting import write_report
from rfc_miner.scoring import score_opportunities
from rfc_miner.standards import compare_standards


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
        self.assertEqual(normalize_path("/jobs/<int:job_id>/cancel"), "/jobs/{var}/cancel")

    def test_source_route_extractor_ignores_test_directories(self) -> None:
        repo = self.fixture_repositories()[1]
        evidence = extract_source_routes(repo, str(repo["local_path"]))
        self.assertFalse(any(record["path"] == "/health" for record in evidence))

    def test_cancellation_requires_strong_cancel_evidence(self) -> None:
        false_positive = classify_route(
            method="GET",
            path="/stacktrace",
            operation_text="request context can be cancelled by clients",
        )
        self.assertEqual(false_positive, [])

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
