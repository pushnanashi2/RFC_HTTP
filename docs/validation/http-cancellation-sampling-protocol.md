# HTTP Cancellation Sampling Protocol

Status: draft for pre-Internet-Draft validation.

This protocol validates whether detected `http-cancellation` evidence represents
operation cancellation rather than ordinary domain state transitions or resource
deletion. It is intentionally narrower than a prevalence study: it validates the
evidence used to motivate a possible Internet-Draft, and it does not turn the
sample into a claim about all HTTP APIs.

## 1. Estimation Targets

The primary inference target is precision over sampled `family_id` × `pattern`
cells, expanded to all cancellation route records inside each selected cell.

A cell is one independent implementation family and one detected cancellation
pattern. The selected cell is labeled by auditing every route record in that
cell. This is a stratified cluster sample: the first-stage unit is the
family-pattern cell, and the second-stage route records inside a selected cell
are included as a census.

The protocol reports three separate layers:

| Layer | Unit | Use |
| --- | --- | --- |
| Strict cancellation frame | `family_id` × strict pattern cell | Primary operation-vs-domain validation |
| `delete-operation-resource` audit | `family_id` × `delete-operation-resource` cell | Distinguish cancellation from deletion or archival, including the unlinked boundary stratum |
| Async-family linkage envelope | async-operation family | Motivation guardrail only, not estimated by this sample |

Do not report a single pooled TP rate over all rows. Route rows inside one cell
are correlated because they share the same repository, family, pattern, and API
design. The effective sample size is therefore closer to the number of selected
cells than to the number of labeled route records.

The sample cannot estimate unique-family prevalence over the 407 strict
cancellation families. Pattern-family cells are non-exclusive, and families with
multiple patterns have multiple inclusion paths.

## 2. Frames and Strata

All counts below use the normalized 5,000-repository snapshot after deterministic
primary-pattern assignment. If the same route has multiple detected cancellation
patterns, the strict explicit-cancel pattern wins over the weaker
`delete-operation-resource` heuristic.

Input frame:

- normalized evidence: `/mnt/cash-data/rfc-http-miner/data-5000-refined/normalized/evidence.jsonl`
- family map: `/mnt/cash-data/rfc-http-miner/data-5000-refined/normalized/families.jsonl`
- clusters: `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/clusters.json`

Generated validation artifacts:

| Artifact | Rows | Purpose |
| --- | ---: | --- |
| `docs/validation/http-cancellation-sample-2026-09-04.csv` | 320 cells | Cell-level sample and machine metadata |
| `docs/validation/http-cancellation-cell-route-sample-2026-09-04.csv` | 635 route rows | All route records inside selected cells |
| `docs/validation/http-cancellation-cell-route-labeling-view-2026-09-04.csv` | 635 route rows | Blinded reviewer worksheet |
| `docs/validation/http-cancellation-cell-route-machine-columns-2026-09-04.csv` | 635 route rows | Hidden machine columns keyed by `evidence_id` |
| `docs/validation/http-cancellation-family-sample-2026-09-04.csv` | 140 families | Descriptive strict-family sensitivity sample |
| `docs/validation/http-cancellation-route-sample-2026-09-04.csv` | 377 routes | Descriptive route-frame sensitivity sample |

Strict cancellation cell frame:

| Pattern | Population cells | Sampled cells | Cell sampling fraction | Route records in selected cells |
| --- | ---: | ---: | ---: | ---: |
| `post-subresource-cancel` | 330 | 80 | 24.2% | 215 |
| `post-action-cancel` | 106 | 35 | 33.0% | 65 |
| `delete-action-cancel` | 31 | 31 | 100.0% | 39 |
| `put-action-cancel` | 27 | 27 | 100.0% | 47 |
| `get-cancel-link` | 18 | 18 | 100.0% | 33 |
| `patch-state-cancelled` | 5 | 5 | 100.0% | 8 |
| **Strict total** | **517** | **196** | — | **407** |

`delete-operation-resource` audit frame:

| Bucket | Population cells | Sampled cells | Cell sampling fraction | Route records in selected cells |
| --- | ---: | ---: | ---: | ---: |
| `delete-only-linked` | 88 | 55 | 62.5% | 99 |
| `delete-and-strict-different-resource` | 47 | 30 | 63.8% | 67 |
| `delete-and-strict-same-resource` | 49 | 15 | 30.6% | 25 |
| `delete-unlinked` | 24 | 24 | 100.0% | 37 |
| **DELETE audit total** | **208** | **124** | — | **228** |

The full observed cancellation membership frame contains 725 cells: 517 strict
cells plus 208 `delete-operation-resource` cells. The inferential validation
frame in this protocol is the same 725-cell frame. The 24 unlinked DELETE cells
are included as a full-census boundary stratum, but they do not affect the
same-resource linkage envelope unless they are reported separately.

## 3. Resource-Level Linkage Envelope

The Internet-Draft motivation must keep the sampling frame separate from the
async-family denominator. The linkage envelope uses 631 async-operation families:

| Component | Families | Denominator | Share |
| --- | ---: | ---: | ---: |
| Strict explicit-cancel families with same-resource async linkage | 194 | 631 | 30.7% |
| Linked `delete-operation-resource` families after primary-pattern assignment | 184 | 631 | 29.2% |
| Family-level overlap between the two linked sets | 96 | 631 | 15.2% |
| Union of the two linked sets | 282 | 631 | 44.7% |

The family-level structural envelope is therefore 194/631 to 282/631 before
manual labels. This 30.7% to 44.7% range is a structural bounding interval, not
a confidence interval and not a prevalence estimate. The upper end means "all
linked DELETE audit candidates are cancellation" and is not `194 + 184` because
overlap families prevent double counting.

Resource-level overlap is smaller than family-level overlap:

| Component | Operation resources |
| --- | ---: |
| Strict linked operation resources | 300 |
| DELETE linked operation resources | 362 |
| Same operation resource in both sets | 57 |
| Resource-level union | 605 |

Among `delete-operation-resource` cells, 49 families have a DELETE route on the
same operation resource as an explicit strict cancel route, while 47 have strict
cancel evidence elsewhere in the same family. This distinction is used for
DELETE audit allocation, but it does not change the family-level upper envelope:
families already counted by the strict lower subset remain counted once.

The two overlap levels intentionally disagree: 96/184 linked DELETE families
also have strict linked cancel evidence somewhere in the family, but only 57/362
linked DELETE operation resources overlap with a strict linked operation
resource. That 52.2% family overlap versus 15.7% resource overlap is direct
evidence that family-level summaries can hide different-resource structure.

## 4. Primary-Pattern Assignment and Identifiers

Primary-pattern assignment removes cross-pattern route duplication before
sampling. The priority order is:

1. `post-subresource-cancel`
2. `post-action-cancel`
3. `delete-action-cancel`
4. `put-action-cancel`
5. `get-cancel-link`
6. `patch-state-cancelled`
7. `delete-operation-resource`

The current raw frame had three route IDs with more than one pattern. After
primary-pattern assignment, all generated CSVs have zero cross-pattern
`route_id` duplicates. Same-pattern `source` and `openapi` evidence may still
share a `route_id`; those are independent evidence rows for the same route and
are joined by `evidence_id`.

Earlier unassigned frame reports counted 185 linked DELETE families and 97
overlap families. The current assigned frame counts 184 and 96. That one-family
movement is a definition change caused by deterministic primary-pattern
assignment, not a correction to the older unassigned run.

Route-row totals can change while the selected cell total is unchanged because
the companion sheet expands every route record inside each selected cell. The
620-to-611 change in the prior run was entirely in `delete-operation-resource`
route rows: strict rows remained 407, while selected DELETE cell contents moved
from 213 to 204 after primary-pattern assignment and bucketed reselection.

Identifiers:

| Column | Definition | Scope |
| --- | --- | --- |
| `route_id` | `sha256(repository, httpMethod, normalizedPath-or-path)` | Stable route identity across commits |
| `evidence_id` | `sha256(route_id, commit, pattern, sourceKind, path, file, lineStart, symbol)` | Stable join key for one sample evidence row |

`evidence_id` is not a raw extractor record identifier. It identifies one
normalized sample evidence row and is the join key between the blinded worksheet
and the machine-column table.

Sampling provenance is stored in each `.summary.json` sidecar rather than in
every CSV row. The current cell sample summary records:

- `seed`: `20260904`
- `samplingCodeCommit`: `dc24a32c27603539079015a9aded627bc9342f36`
- `pythonVersion`: `3.10.12`
- `frameSnapshotHash`: `36035d4b0fc6d94b0342fe196b20d4ff4ac26c6fb44d607e9909d4acf4f07da5`

## 5. Selection Rules

The representative cell sheet is deterministic for the same frame, seed, Python
version, and sampling code commit.

Cell selection:

- sample within pattern or DELETE-audit bucket;
- sort family IDs before shuffling;
- shuffle with `random.Random(f"{seed}:{pattern}:{bucket}")`;
- cap each repository at two rows per pattern and five rows total;
- for `delete-operation-resource`, sample 55 cells from `delete-only-linked`,
  30 from `delete-and-strict-different-resource`, 15 from
  `delete-and-strict-same-resource`, and all 24 from `delete-unlinked`.

Representative route selection inside a selected cell:

- sort candidate route rows by stable identity fields;
- select one row uniformly with `random.Random(f"{seed}:cell-route:{pattern}:{family_id}")`;
- do not prefer route-level async linkage, HTTP `202`, `sourceKind`, or
  confidence.

The representative row exists for inspection and reproducibility. It is not the
only labeled record. The companion cell-route sheet includes every cancellation
route record in every selected cell.

## 6. Label Taxonomies

Use one taxonomy for strict cancellation cells and a separate taxonomy for
`delete-operation-resource` cells.

Strict operation-vs-domain taxonomy:

- `operation-cancellation`: the route cancels an observable operation, job, task,
  run, execution, workflow, build, deployment, pipeline, export, import, backup,
  restore, sync, scan, render, transcode, training, migration, index, provision,
  snapshot, report, query, status monitor, or equivalent operation handle.
- `domain-state-transition`: the route cancels a business object such as a
  subscription, order, booking, plan, invoice, reservation, account, request, or
  membership.
- `ambiguous`: the available route, operation name, response semantics, and
  bounded adjacent context do not prove which of the two applies.

DELETE audit taxonomy:

- `cancellation`: the DELETE route requests cancellation of an ongoing operation.
- `deletion-or-archival`: the DELETE route removes, archives, garbage-collects,
  or forgets an operation resource after or independent of execution.
- `ambiguous`: the available evidence does not distinguish cancellation from
  deletion, archival, or garbage collection.

When reporting DELETE audit TP-style rates, map `cancellation` to the positive
class, map `deletion-or-archival` to the negative class, and apply the ambiguity
bounds below to `ambiguous`.

Path nouns alone are never sufficient. If the evidence does not settle the
semantics, choose `ambiguous`.

## 7. Blinded Labeling Procedure

Labelers use
`docs/validation/http-cancellation-cell-route-labeling-view-2026-09-04.csv`.
Machine-generated columns are physically separated into
`docs/validation/http-cancellation-cell-route-machine-columns-2026-09-04.csv`.
Join the two files only after final labels are recorded.

Hidden from labelers during the first pass:

- `pattern`
- `routeStratum`
- `linkageBucket`
- `deleteOperationResourceBucket`
- `familyPatternHasSameResourceLinked`
- `familyPatternHasOperationTarget`
- `familyPatternHasDomainTransitionRisk`
- `routeLevelOperationLinked`
- `operationTarget`
- `domainTransitionRisk`
- `confidence`
- `cancelTargetPath`
- precomputed adjacent-linkage evidence

Visible reviewer context:

- `repository`
- `commit`
- `httpMethod`
- `normalizedPath`
- original `path`
- `sourceKind`
- `file`
- `lineStart`
- `symbol`
- `responseCodes`
- bounded response semantics evidence

Workflow:

1. Produce an LLM draft label for each route row using only the blinded evidence
   packet for that row.
2. Require a verbatim quote from the evidence packet and a one-sentence rationale.
3. Verify mechanically that each quoted string exists in the packet.
4. Human-adjudicate every labeled route row.
5. Aggregate route labels back to `cell_sample_id` before computing cell-stratum
   estimates.

The worksheet contains an `unanchored_subset` marker for 80 sampled cells. Those
cells are selected by deterministic stratum-aware allocation over the generated
cell sheet: each non-empty selected stratum gets at least one cell when capacity
allows, and the remaining cells are allocated proportionally. For those cells,
human reviewers must not see the LLM draft before recording independent labels.
Use that subset to estimate anchoring effects and human-human agreement.

## 8. Adjudication and Agreement

All route rows require a final adjudicated label before estimator scripts run.
Only `final_label` counts for estimation.

Recommended worksheet fields:

- `draft_label`
- `draft_quote`
- `draft_rationale`
- `labeler_a_label`
- `labeler_a_quote`
- `labeler_a_rationale`
- `labeler_b_label`
- `labeler_b_quote`
- `labeler_b_rationale`
- `final_label`
- `adjudicator`
- `changed_from_draft`
- `note`

Report agreement separately from sampling uncertainty:

- LLM draft vs final human label over all rows;
- human-human raw agreement and Cohen's kappa on the 80-cell unanchored subset;
- disagreement counts by stratum and taxonomy.

Kappa is a reliability diagnostic, not a pass/fail threshold.

## 9. Estimators and Intervals

Because the design is a stratified cluster sample, do not use pooled
Clopper-Pearson, Wilson, or Wald intervals over route rows.

For each stratum `h`, selected cell `i`, and route record `j`:

- `m_hi`: number of labeled route records in selected cell `i`;
- `y_hij`: positive-class indicator for route `j`;
- `Y_hi = Σ_j y_hij`;
- `R_h = Σ_i Y_hi / Σ_i m_hi`.

`R_h` is a route-ratio estimator within sampled cells. It is not the simple
average of cell-level proportions when cell sizes differ.

For the strict overall estimate, combine strict strata with known frame totals.
For the DELETE audit, combine the four DELETE buckets separately and keep the
unlinked census bucket visible as a boundary stratum. Do not combine DELETE audit
rows into the strict denominator unless the strict definition is explicitly
changed.

Ambiguity bounds:

| Variant | Positive numerator |
| --- | --- |
| `ambiguous_excluded` | positives among non-ambiguous rows only |
| `ambiguous_as_fp` | positives, with ambiguous rows counted negative |
| `ambiguous_as_tp` | positives plus ambiguous rows |

Intervals:

- primary interval: stratified cluster bootstrap;
- resample selected cells with replacement inside each non-census stratum;
- keep all route records in a resampled cell together;
- keep census strata fixed because their cell-selection variance is zero;
- use 5,000 bootstrap replicates by default;
- report percentile 95% intervals for each ambiguity variant.

The census strata are:

- `delete-action-cancel`
- `put-action-cancel`
- `get-cancel-link`
- `patch-state-cancelled`
- `delete-unlinked` within the DELETE audit

The non-census strict strata are:

- `post-subresource-cancel`
- `post-action-cancel`

The non-census DELETE audit strata are:

- `delete-only-linked`
- `delete-and-strict-different-resource`
- `delete-and-strict-same-resource`

Report ICC and design effect for each stratum and ambiguity variant:

```text
DEFF_h = 1 + (mean_cluster_size_h - 1) * ICC_h
effective_n_h = labeled_route_records_h / DEFF_h
```

ICC and DEFF are findings, not mere diagnostics. If ICC is high, cell-level
semantics dominate and the cluster design is justified. If ICC is low,
family-pattern cells hide meaningful route-level heterogeneity.

## 10. Role of Other Samples

The 140-row strict-family sample and 377-row route-record sample are descriptive
sensitivity artifacts.

Use them for:

- sanity-checking whether conclusions change under a different unit;
- inspecting generated-catalog concentration;
- motivating extractor improvements;
- selecting examples for the draft.

Do not use them to replace the primary 320-cell cluster design unless the
protocol is revised and the estimand is changed.

## 11. Known Limitations

- The protocol estimates evidence precision for the current detection frame, not
  prevalence among all HTTP APIs.
- The async-family denominator is 631 families; the validation frame is 725
  sampled-eligible cells. Keep these denominators separate.
- Route rows inside a cell can contain mixed operation and domain semantics; the
  all-routes companion sheet measures that mixing directly for selected cells.
- The unlinked 24 `delete-operation-resource` cells are sampled as a full-census
  boundary stratum, but they are not part of the same-resource linked envelope.
- The 30.7% to 44.7% linkage range is a structural bounding interval. Sampling
  confidence intervals are computed separately after labels are available.
- Same-pattern `source` and `openapi` rows can share a `route_id`; use
  `evidence_id` for worksheet joins.
- Cross-pattern route duplication was rare in the raw frame and is removed by
  deterministic primary-pattern assignment before sampling.
- Labeling uncertainty is separate from sampling uncertainty; report agreement
  and anchoring diagnostics alongside confidence intervals.

## 12. Reproduction Commands

Generate the primary cell sheet:

```bash
rfc-miner sample-cancellation \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --profile full \
  --output docs/validation/http-cancellation-sample-2026-09-04.csv
```

Generate all route rows inside selected cells:

```bash
rfc-miner sample-cancellation-cell-routes \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --profile full \
  --output docs/validation/http-cancellation-cell-route-sample-2026-09-04.csv
```

Generate blinded reviewer and machine-column files:

```bash
rfc-miner split-cancellation-labeling-view \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --input docs/validation/http-cancellation-cell-route-sample-2026-09-04.csv \
  --labeling-output docs/validation/http-cancellation-cell-route-labeling-view-2026-09-04.csv \
  --machine-output docs/validation/http-cancellation-cell-route-machine-columns-2026-09-04.csv \
  --unanchored-size 80
```
