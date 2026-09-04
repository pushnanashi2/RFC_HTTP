# Stage-1 Data

This directory contains the latest Stage-1 run of `rfc-miner` over the
30-repository HTTP API seed corpus.

Run command:

```bash
PYTHONPATH=src python3 -m rfc_miner.cli run --limit 30 --data-dir data --repo-dir data/repos
```

The run uses streaming checkout cleanup by default, so repository checkouts are
not retained in `data/repos`.

Key outputs:

- `raw/repositories.jsonl`
- `raw/evidence.jsonl`
- `raw/errors.jsonl`
- `normalized/evidence.jsonl`
- `normalized/families.jsonl`
- `results/report.md`
- `results/manual-review.md`
- `results/candidates/http-async-operation.md`
- `results/candidates/http-cancellation.md`
