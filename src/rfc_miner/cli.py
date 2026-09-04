from __future__ import annotations

import argparse
import os
from pathlib import Path

from .clustering import cluster_patterns
from .collector import collect_repositories
from .deduplication import dedupe_repositories
from .extraction import analyze_repositories
from .github_discovery import discover_github_repositories
from .normalization import normalize_evidence
from .paths import data_paths
from .reporting import write_report
from .sampling import (
    write_cancellation_family_sample,
    write_cancellation_route_sample,
    write_cancellation_sample,
)
from .scoring import score_opportunities
from .standards import compare_standards
from .streaming import collect_and_analyze_streaming


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_REL = Path("config") / "corpus" / "stage1-http.json"
DEFAULT_STANDARDS_REL = Path("config") / "standards" / "http-api-seed.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rfc-miner")
    subcommands = parser.add_subparsers(dest="command", required=True)

    discover = subcommands.add_parser("discover-github", help="discover GitHub repositories for a large corpus seed")
    add_common(discover)
    discover.add_argument("--output", default="data/raw/github-discovered-seed.json")
    discover.add_argument("--target", type=int, default=5000)
    discover.add_argument("--min-stars", type=int, default=20)
    discover.add_argument("--updated-since", default="2024-01-01")
    discover.add_argument("--per-query-limit", type=int, default=200)
    discover.add_argument("--max-size-kb", type=int, default=250_000)
    discover.add_argument("--fresh", action="store_true")

    collect = subcommands.add_parser("collect", help="collect and pin repositories")
    add_common(collect)
    collect.add_argument("--seed", default=str(default_path(DEFAULT_SEED_REL)))
    collect.add_argument("--repo-dir", default=default_repo_dir())
    collect.add_argument("--limit", type=int, default=30)
    collect.add_argument("--no-clone", action="store_true")

    analyze = subcommands.add_parser("analyze", help="extract raw evidence")
    add_common(analyze)
    analyze.add_argument("--repositories")

    normalize = subcommands.add_parser("normalize", help="normalize raw evidence")
    add_common(normalize)
    normalize.add_argument("--raw-evidence")

    dedupe = subcommands.add_parser("dedupe", help="map repos to independent families")
    add_common(dedupe)
    dedupe.add_argument("--repositories")
    dedupe.add_argument("--normalized-evidence")

    cluster = subcommands.add_parser("cluster", help="cluster normalized patterns")
    add_common(cluster)

    compare = subcommands.add_parser("compare-standards", help="compare with seeded standards")
    add_common(compare)
    compare.add_argument("--standards", default=str(default_path(DEFAULT_STANDARDS_REL)))

    score = subcommands.add_parser("score", help="score opportunities")
    add_common(score)

    report = subcommands.add_parser("report", help="write Markdown report")
    add_common(report)

    cancellation_sample = subcommands.add_parser(
        "sample-cancellation",
        help="write a stratified HTTP cancellation validation sample sheet",
    )
    add_common(cancellation_sample)
    cancellation_sample.add_argument("--output")
    cancellation_sample.add_argument("--profile", choices=["full", "minimum"], default="full")
    cancellation_sample.add_argument("--seed", type=int, default=20260904)

    cancellation_family_sample = subcommands.add_parser(
        "sample-cancellation-family",
        help="write a strict-family HTTP cancellation validation sample sheet",
    )
    add_common(cancellation_family_sample)
    cancellation_family_sample.add_argument("--output")
    cancellation_family_sample.add_argument("--profile", choices=["full", "minimum"], default="full")
    cancellation_family_sample.add_argument("--seed", type=int, default=20260904)

    cancellation_route_sample = subcommands.add_parser(
        "sample-cancellation-routes",
        help="write a route-record HTTP cancellation validation sample sheet",
    )
    add_common(cancellation_route_sample)
    cancellation_route_sample.add_argument("--output")
    cancellation_route_sample.add_argument("--profile", choices=["full", "minimum"], default="full")
    cancellation_route_sample.add_argument("--seed", type=int, default=20260904)

    run = subcommands.add_parser("run", help="run the full pipeline")
    add_common(run)
    run.add_argument("--seed", default=str(default_path(DEFAULT_SEED_REL)))
    run.add_argument("--repo-dir", default=default_repo_dir())
    run.add_argument("--limit", type=int, default=30)
    run.add_argument("--repositories")
    run.add_argument("--standards", default=str(default_path(DEFAULT_STANDARDS_REL)))
    run.add_argument("--skip-collect", action="store_true")
    run.add_argument("--no-clone", action="store_true")
    run.add_argument("--keep-repos", action="store_true")
    run.add_argument("--fresh", action="store_true")
    run.add_argument("--jobs", type=int, default=int(os.environ.get("RFC_MINER_JOBS", "1")))
    run.add_argument("--flush-interval", type=int, default=int(os.environ.get("RFC_MINER_FLUSH_INTERVAL", "25")))

    return parser


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-dir", default=os.environ.get("RFC_MINER_DATA_DIR", "data"))


def default_repo_dir() -> str:
    return os.environ.get("RFC_MINER_REPO_DIR", "data/repos")


def default_path(relative_path: Path) -> Path:
    cwd_candidate = Path.cwd() / relative_path
    if cwd_candidate.exists():
        return cwd_candidate
    return PROJECT_ROOT / relative_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = data_paths(args.data_dir)

    if args.command == "collect":
        records = collect_repositories(
            seed_path=args.seed,
            paths=paths,
            repo_dir=args.repo_dir,
            limit=args.limit,
            clone=not args.no_clone,
        )
        print(f"collected repositories: {len(records)}")
        return 0

    if args.command == "discover-github":
        result = discover_github_repositories(
            output_path=args.output,
            target=args.target,
            min_stars=args.min_stars,
            updated_since=args.updated_since,
            per_query_limit=args.per_query_limit,
            max_size_kb=args.max_size_kb,
            resume=not args.fresh,
        )
        print(f"discovered repositories: {len(result.get('repositories', []))}; output: {args.output}")
        return 0

    if args.command == "analyze":
        evidence, errors = analyze_repositories(paths=paths, repositories_path=args.repositories)
        print(f"raw evidence: {len(evidence)}; errors: {len(errors)}")
        return 0

    if args.command == "normalize":
        records = normalize_evidence(paths=paths, raw_evidence_path=args.raw_evidence)
        print(f"normalized evidence: {len(records)}")
        return 0

    if args.command == "dedupe":
        families = dedupe_repositories(
            paths=paths,
            repositories_path=args.repositories,
            normalized_evidence_path=args.normalized_evidence,
        )
        print(f"families: {len(families)}")
        return 0

    if args.command == "cluster":
        clusters = cluster_patterns(paths=paths)
        print(f"concept clusters: {len(clusters.get('concepts', {}))}")
        return 0

    if args.command == "compare-standards":
        comparisons = compare_standards(paths=paths, standards_path=args.standards)
        print(f"standards comparisons: {len(comparisons.get('concepts', {}))}")
        return 0

    if args.command == "score":
        scores = score_opportunities(paths=paths)
        print(f"opportunity scores: {len(scores.get('scores', []))}")
        return 0

    if args.command == "report":
        write_report(paths=paths)
        print(f"report: {paths.report}")
        return 0

    if args.command == "sample-cancellation":
        output, count = write_cancellation_sample(
            paths=paths,
            output_path=args.output,
            profile=args.profile,
            seed=args.seed,
        )
        print(f"cancellation sample: {output}; rows: {count}")
        return 0

    if args.command == "sample-cancellation-family":
        output, count = write_cancellation_family_sample(
            paths=paths,
            output_path=args.output,
            profile=args.profile,
            seed=args.seed,
        )
        print(f"cancellation family sample: {output}; rows: {count}")
        return 0

    if args.command == "sample-cancellation-routes":
        output, count = write_cancellation_route_sample(
            paths=paths,
            output_path=args.output,
            profile=args.profile,
            seed=args.seed,
        )
        print(f"cancellation route sample: {output}; rows: {count}")
        return 0

    if args.command == "run":
        if not args.skip_collect:
            if args.no_clone:
                collect_repositories(
                    seed_path=args.seed,
                    paths=paths,
                    repo_dir=args.repo_dir,
                    limit=args.limit,
                    clone=False,
                )
                analyze_repositories(paths=paths)
            else:
                collect_and_analyze_streaming(
                    seed_path=args.seed,
                    paths=paths,
                    repo_dir=args.repo_dir,
                    limit=args.limit,
                    keep_repos=args.keep_repos,
                    resume=not args.fresh,
                    jobs=args.jobs,
                    flush_interval=args.flush_interval,
                )
            repositories_path = None
        else:
            repositories_path = args.repositories
            analyze_repositories(paths=paths, repositories_path=repositories_path)
        normalize_evidence(paths=paths)
        dedupe_repositories(paths=paths)
        cluster_patterns(paths=paths)
        compare_standards(paths=paths, standards_path=args.standards)
        score_opportunities(paths=paths)
        write_report(paths=paths)
        print(f"report: {paths.report}")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
