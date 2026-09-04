# RFC HTTP Miner

RFC HTTP Miner is an evidence-first OSS analysis tool for finding HTTP API
standardization opportunities. It is designed to measure convergent and
divergent implementation practice across many repositories without putting an
LLM at the center of classification.

The first vertical slice focuses on two concepts:

- HTTP asynchronous operations
- HTTP cancellation operations

The pipeline is intentionally staged and resumable:

```text
OSS corpus
  -> collection
  -> extraction
  -> normalization
  -> deduplication
  -> clustering
  -> standards comparison
  -> scoring
  -> report
```

## Install for local development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Run the fixture pipeline

```bash
rfc-miner run \
  --repositories tests/fixtures/data/raw/repositories.jsonl \
  --data-dir .tmp/fixture-run \
  --skip-collect
```

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Run the stage-1 corpus

This clones shallow, commit-pinned copies into `data/repos` and writes a
machine-readable repository inventory.

```bash
rfc-miner run \
  --seed config/corpus/stage1-http.json \
  --limit 30 \
  --data-dir data \
  --repo-dir data/repos
```

Each stage can also be run independently:

```bash
rfc-miner collect
rfc-miner analyze
rfc-miner normalize
rfc-miner dedupe
rfc-miner cluster
rfc-miner compare-standards
rfc-miner score
rfc-miner report
```

## Key outputs

- `data/raw/repositories.jsonl` — collected repositories and pinned commits
- `data/raw/evidence.jsonl` — extracted evidence with file, symbol, line, and extractor version
- `data/normalized/evidence.jsonl` — normalized paths and interaction patterns
- `data/normalized/families.jsonl` — raw repo to independent implementation family mapping
- `data/results/clusters.json` — pattern counts, entropy, and family prevalence
- `data/results/standards-comparison.json` — seeded standards coverage comparison
- `data/results/opportunity-scores.json` — scored RFC candidates
- `data/results/report.md` — human-readable stage report
- `data/results/manual-review.md` — TP/FP/FN validation checklist

## Design documents

- `docs/research-design.md`
- `docs/architecture.md`
- `docs/evolution-log.md`
