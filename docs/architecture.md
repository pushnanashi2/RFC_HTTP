# Architecture

## Goals

RFC HTTP Miner is a staged pipeline for discovering HTTP API standardization
opportunities from OSS evidence. The system optimizes for auditability over
coverage: a smaller corpus with traceable evidence is better than a larger
opaque classification.

## Pipeline

```text
collect
  -> analyze
  -> normalize
  -> dedupe
  -> cluster
  -> compare-standards
  -> score
  -> report
```

Each stage reads and writes files under `data/` by default. The CLI accepts
alternate paths so tests and experiments can run without touching production
data.

`run` uses a streaming collector/analyzer by default: it clones one repository,
pins the commit, extracts evidence, writes intermediate artifacts, and removes
the checkout unless `--keep-repos` is passed. This keeps the Stage-1 corpus
workable on small disks while preserving reproducible commit hashes.

Large runs can move temporary checkouts and generated data with
`RFC_MINER_REPO_DIR` and `RFC_MINER_DATA_DIR`.

## Modules

- `rfc_miner.collector`: seed-based GitHub repository collection and commit
  pinning.
- `rfc_miner.extraction`: repository-level orchestration and error capture.
- `rfc_miner.extractors.openapi`: OpenAPI/Swagger JSON plus lightweight YAML
  operation extraction.
- `rfc_miner.extractors.source_routes`: deterministic source-route extraction
  for common HTTP server idioms.
- `rfc_miner.normalization`: path normalization and concept pattern assignment.
- `rfc_miner.deduplication`: raw repository to independent implementation
  family mapping.
- `rfc_miner.clustering`: prevalence, pattern counts, entropy, and
  concentration metrics.
- `rfc_miner.standards`: seeded standards comparison.
- `rfc_miner.scoring`: visible RFC opportunity score components.
- `rfc_miner.reporting`: Markdown reports and candidate detail files.

## Data Layout

```text
data/
  raw/
    repositories.jsonl
    evidence.jsonl
    errors.jsonl
  normalized/
    evidence.jsonl
    families.jsonl
  results/
    clusters.json
    standards-comparison.json
    opportunity-scores.json
    report.md
    candidates/
```

## Common IR

The common IR is intentionally small. Every extractor emits the same evidence
shape:

```json
{
  "repository": "owner/name",
  "commit": "abc123",
  "concept": "http-cancellation",
  "evidenceType": "route",
  "httpMethod": "POST",
  "path": "/jobs/{id}/cancel",
  "responseCodes": [202],
  "file": "src/routes.ts",
  "symbol": "cancelJob",
  "lineStart": 81,
  "lineEnd": 103,
  "confidence": 0.98,
  "extractor": "source-routes",
  "extractorVersion": "0.1.0"
}
```

The repository, evidence, and family records are pinned as JSON Schemas under
`schemas/`.

## Failure Handling

Repository failures are written as structured records:

```json
{
  "repo": "owner/name",
  "stage": "analyze",
  "errorType": "parse_error",
  "error": "message",
  "retryable": false
}
```

One broken repository must not stop the corpus.

## LLM Boundary

LLMs are not used for extraction, counting, or scoring. They may generate review
candidates for unknown terms or standards-gap prose, but the accepted rules must
be written as configuration or code and linked to evidence.

## Initial Vertical Slice

The first slice supports:

- OpenAPI JSON route extraction
- lightweight OpenAPI YAML route extraction
- common source route extraction
- async/cancellation concept classification
- route normalization
- independent family approximation
- pattern clustering
- seeded standards coverage
- opportunity scoring
- Markdown reporting

This slice is deliberately replaceable: future AST extractors should emit the
same IR rather than changing downstream analysis.
