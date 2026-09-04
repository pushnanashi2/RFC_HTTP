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

The default `run` mode clones one repository at a time, pins its commit,
extracts evidence, and removes the checkout after analysis. Pass `--keep-repos`
when you want to keep shallow copies in `data/repos` for debugging.

For large corpus runs, put temporary checkouts on a large external disk:

```bash
export RFC_MINER_REPO_DIR=/mnt/cash-data/rfc-http-miner/repos
export RFC_MINER_DATA_DIR=/mnt/cash-data/rfc-http-miner/data
```

```bash
rfc-miner run \
  --seed config/corpus/stage1-http.json \
  --limit 30 \
  --data-dir data \
  --repo-dir data/repos
```

Each stage can also be run independently:

```bash
rfc-miner discover-github --target 5000
rfc-miner collect
rfc-miner analyze
rfc-miner normalize
rfc-miner dedupe
rfc-miner cluster
rfc-miner compare-standards
rfc-miner score
rfc-miner report
```

## Discover a 5000 repository seed

```bash
rfc-miner discover-github \
  --target 5000 \
  --output /mnt/cash-data/rfc-http-miner/github-http-5000.json \
  --max-size-kb 250000 \
  --per-query-limit 300
```

Then run the corpus in streaming mode:

```bash
rfc-miner run \
  --seed /mnt/cash-data/rfc-http-miner/github-http-5000.json \
  --limit 5000 \
  --jobs 12 \
  --flush-interval 25
```

If the run is interrupted, run the same command again to resume. Use `--fresh`
only when you intentionally want to overwrite the current stage output.
Discovery shards are interleaved by search term and language so an early
5,000-repository stop does not fill the corpus from only the first language.
Generated SDKs, API clients, templates, tutorials, prompt packs, editor
extensions, GitHub Actions, and very large repositories are filtered before the
seed is written.

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
- `docs/runs/2026-09-04-5000-final.md`
