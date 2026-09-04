# HTTP Cancellation Sampling Protocol

Status: draft for pre-Internet-Draft validation.

## Goal

Estimate how much detected `http-cancellation` evidence is actually operation
cancellation rather than business-domain cancellation.

The protocol is designed to protect the Internet-Draft motivation from the
largest precision risk: routes such as `POST /subscriptions/{id}/cancel`,
`POST /orders/{id}/cancel`, and `POST /bookings/{id}/cancel` have the same shape
as `POST /jobs/{id}/cancel`, but can represent ordinary domain state
transitions.

## Sampling Frame

Input:

- normalized evidence: `/mnt/cash-data/rfc-http-miner/data-5000-refined/normalized/evidence.jsonl`
- family map: `/mnt/cash-data/rfc-http-miner/data-5000-refined/normalized/families.jsonl`
- clusters: `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/clusters.json`

Generate the sheet:

```bash
rfc-miner sample-cancellation \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --profile full
```

Default output:

- `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/validation/http-cancellation-sample.csv`
- `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/validation/http-cancellation-sample.summary.json`

Current generated snapshot:

- `docs/validation/http-cancellation-sample-2026-09-04.csv`
- `docs/validation/http-cancellation-sample-2026-09-04.summary.json`

Sampling unit:

- one deduplicated evidence record, grouped by `family_id`, `repository`,
  `pattern`, `httpMethod`, `normalizedPath`, and `sourceKind`.

Primary population:

- strict cancellation patterns:
  - `post-subresource-cancel`
  - `post-action-cancel`
  - `put-action-cancel`
  - `get-cancel-link`
  - `patch-state-cancelled`
  - `delete-action-cancel`

Secondary audit population:

- `delete-operation-resource`, because it has the strongest route-level linkage
  signal but is semantically ambiguous without explicit cancel wording.
  Its operation-like-target and domain-transition-risk counts are mostly
  definition-derived, so the informative pre-sampling signal is same-resource
  async linkage.

## Current Strata

Rows are non-exclusive pattern-family memberships and must not be summed.

| Pattern | Families | Same-resource linked | Operation target | Domain-transition risk | Proposed sample |
| --- | ---: | ---: | ---: | ---: | ---: |
| `post-subresource-cancel` | 330 | 155 | 173 | 246 | 80 |
| `post-action-cancel` | 106 | 31 | 34 | 80 | 50 |
| `delete-action-cancel` | 31 | 19 | 24 | 8 | 30 |
| `put-action-cancel` | 27 | 7 | 10 | 21 | 27 |
| `get-cancel-link` | 18 | 4 | 4 | 16 | 18 |
| `patch-state-cancelled` | 5 | 1 | 2 | 3 | 5 |
| `delete-operation-resource` | 209 | 185 | 202 | 0 | 50 |

Total proposed sample size: 260 records.

For `delete-operation-resource`, use the 185/209 same-resource linkage as the
reason to sample the bucket. Do not treat 202/209 operation-like target or zero
domain-transition risk as independent evidence of precision.

If reviewer time is constrained, use a 140-record minimum sample:

| Pattern | Minimum sample |
| --- | ---: |
| `post-subresource-cancel` | 50 |
| `post-action-cancel` | 30 |
| `delete-action-cancel` | 20 |
| `put-action-cancel` | 15 |
| `get-cancel-link` | 10 |
| `patch-state-cancelled` | 5 |
| `delete-operation-resource` | 10 |

## Secondary Repository Stratification

Sampling must avoid letting one large repository or generated catalog dominate a
pattern stratum.

Rules:

- sample families first, then choose one evidence record per selected family;
- cap each repository at two samples per pattern;
- cap each repository at five total samples across the whole sheet;
- preserve both `openapi` and `source` examples when they expose materially
  different route evidence;
- if a cap prevents filling a stratum, continue with the next random family in
  that pattern.

For generated catalog audits, run a separate concentration sample rather than
relaxing these caps.

## Linkage Sub-Strata

Within each pattern, sample across three route-level buckets when available:

- same-resource async linked;
- operation-like target without same-resource linkage;
- domain-transition risk.

For `post-subresource-cancel`, prefer roughly balanced thirds across the three
buckets because it is both the dominant shape and the largest precision risk.

For small strata, include all available records and mark the missing linkage
buckets as empty rather than oversampling another bucket without notation.

## Labels

Use exactly one primary label:

- `operation-cancellation`: the canceled target is an observable operation, job,
  task, run, execution, workflow, build, deployment, pipeline, status monitor, or
  equivalent operation handle.
- `domain-state-transition`: the canceled target is a business object such as a
  subscription, order, booking, plan, invoice, reservation, request, account, or
  membership, and the evidence does not tie that same target to operation
  status/progress/result observation.
- `ambiguous`: the route suggests cancellation, but the available route,
  operation name, response codes, and adjacent paths do not prove whether the
  target is an operation or a business object.

Use secondary flags when applicable:

- `extractor_false_positive`: the route was not a server-side HTTP API route or
  was classified from unrelated text.
- `generated_duplicate`: the record appears to be generated from a copied
  catalog or repeated spec source.
- `needs_adjacent_context`: the label depends on nearby routes not included in
  the sampled record.

## Label Sheet Columns

Required columns:

- `sample_id`
- `family_id`
- `repository`
- `pattern`
- `httpMethod`
- `normalizedPath`
- `sourceKind`
- `file`
- `lineStart`
- `cancelTargetPath`
- `routeLevelOperationLinked`
- `operationTarget`
- `domainTransitionRisk`
- `primaryLabel`
- `secondaryFlags`
- `reviewerConfidence`
- `rationale`
- `adjacentOperationEvidence`
- `terminalStateEvidence`
- `responseSemanticsEvidence`
- `reviewer`
- `adjudicatedLabel`

Recommended `reviewerConfidence` values:

- `high`: route and adjacent evidence clearly identify the target semantics;
- `medium`: route semantics are likely but missing one supporting signal;
- `low`: label relies on naming only.

## Review Process

1. Generate the sample sheet from normalized evidence and family data.
2. Two reviewers label each record independently.
3. Measure agreement before discussion.
4. Adjudicate disagreements into `adjudicatedLabel`.
5. Record common false-positive causes and update extractor or linkage rules
   only after adjudication.
6. Recompute corrected prevalence from adjudicated labels.

Agreement metrics:

- report raw agreement by label;
- report Cohen's kappa if both reviewers complete the same sample;
- list all records where one reviewer chose `operation-cancellation` and the
  other chose `domain-state-transition`.

## TP Rate and Confidence Intervals

For each pattern stratum, compute:

- `n`: adjudicated sample size;
- `tp`: records labeled `operation-cancellation`;
- `ambiguous`: records labeled `ambiguous`;
- `tp_rate`: `tp / n`;
- `strict_tp_rate`: `tp / (n - ambiguous)` when `n - ambiguous > 0`;
- Wilson 95% confidence interval for `tp_rate`.

Wilson interval:

```text
center = (p + z²/(2n)) / (1 + z²/n)
margin = z * sqrt((p(1-p) + z²/(4n)) / n) / (1 + z²/n)
z = 1.96
```

For the overall strict cancellation estimate, use a stratified weighted
estimate:

```text
weighted_tp_rate = sum(pattern_family_count * pattern_tp_rate) / sum(pattern_family_count)
```

Report separate totals for:

- strict cancellation only;
- strict same-resource linked cancellation;
- strict operation-like target cancellation;
- `delete-operation-resource` audit evidence.

Do not combine `delete-operation-resource` into the strict denominator unless
the adjudicated sample justifies changing the strict definition.

## Acceptance Thresholds For Drafting

Proceed to an Internet-Draft skeleton if:

- `post-subresource-cancel` operation-cancellation TP rate is high enough that
  the dominant-shape argument survives manual review;
- the weighted strict cancellation TP rate is published with confidence
  intervals and caveats;
- domain-state-transition examples are explicitly acknowledged in the
  motivation;
- `delete-operation-resource` is either kept as supporting evidence or promoted
  through a documented rule change.

If these conditions fail, keep `http-cancellation` as a section of the broader
operation-resource study rather than a standalone draft.
