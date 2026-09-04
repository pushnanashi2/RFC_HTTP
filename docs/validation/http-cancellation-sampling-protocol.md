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

Generate the primary route-record sheet:

```bash
rfc-miner sample-cancellation-routes \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --profile full
```

Default output:

- `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/validation/http-cancellation-route-sample.csv`
- `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/validation/http-cancellation-route-sample.summary.json`

Generate the support pattern-family sheet:

```bash
rfc-miner sample-cancellation \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --profile full
```

Default output:

- `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/validation/http-cancellation-sample.csv`
- `/mnt/cash-data/rfc-http-miner/data-5000-refined/results/validation/http-cancellation-sample.summary.json`

Current generated snapshot:

- `docs/validation/http-cancellation-route-sample-2026-09-04.csv`
- `docs/validation/http-cancellation-route-sample-2026-09-04.summary.json`
- `docs/validation/http-cancellation-sample-2026-09-04.csv`
- `docs/validation/http-cancellation-sample-2026-09-04.summary.json`
- `docs/validation/http-cancellation-family-sample-2026-09-04.csv`
- `docs/validation/http-cancellation-family-sample-2026-09-04.summary.json`

Sampling unit:

- primary route sheet: one deduplicated cancellation route record. Route
  strata are exclusive in this sheet, so a route-record TP rate can be estimated
  with ordinary stratum weights.
- support pattern sheet: one `family_id` × `pattern` membership, represented by
  the highest-quality evidence record for that membership.
- family denominator sheet: one strict cancellation `family_id`, represented by
  the highest-quality strict cancellation evidence record for that family.
- the support pattern sheet must not contain two rows with the same `family_id`
  and `pattern`; the family sheet must not contain two rows with the same
  `family_id`.
- the route sheet estimates route-record precision. It does not update the 407
  strict unique-family denominator.
- the support pattern sheet estimates pattern-family membership precision. It
  does not estimate route-record precision or unique-family prevalence.

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

## Operation-Resource Denominator

Strict/non-strict scoring is orthogonal to operation-vs-domain semantics. The
Internet-Draft motivation should therefore describe an operation-resource
linkage envelope before any single prevalence claim:

| Component | Families | Async-operation denominator | Share | Use |
| --- | ---: | ---: | ---: | --- |
| Strict explicit-cancel routes with same-resource async linkage | 194 | 631 | 30.7% | lower structural subset |
| `delete-operation-resource` routes with same-resource async linkage | 185 | 631 | 29.3% | promotion-audit swing factor |
| Overlap between those linked sets | 97 | 631 | 15.4% | prevents double counting |
| Union of strict-linked and delete-linked sets | 282 | 631 | 44.7% | pre-label upper structural envelope |

The earlier maximum `194 + 185 = 379` is not a defensible upper bound because 97
families are in both linked sets. The current structural envelope is therefore
194/631 to 282/631 before manual labels. Treat this as a linkage envelope, not
as a true-positive rate.

## Current Route-Record Primary Strata

The primary sheet uses exclusive route-record strata. This is the only current
sample whose design supports one weighted operation-cancellation TP estimate
over cancellation route records.

| Route stratum | Population route records | Sampled route records | Sampling fraction | Estimation role |
| --- | ---: | ---: | ---: | --- |
| `delete-operation-resource:any` | 468 | 100 | 21.4% | largest swing factor for the operation-resource envelope |
| `post-subresource-cancel:linked` | 257 | 30 | 11.7% | already same-resource linked |
| `post-subresource-cancel:unlinked` | 617 | 70 | 11.3% | dominant domain-transition-risk queue |
| `post-action-cancel:any` | 189 | 50 | 26.5% | secondary explicit-cancel shape |
| `delete-action-cancel:any` | 39 | 39 | 100.0% | full census |
| `put-action-cancel:any` | 47 | 47 | 100.0% | full census |
| `get-cancel-link:any` | 33 | 33 | 100.0% | full census |
| `patch-state-cancelled:any` | 8 | 8 | 100.0% | full census |

Total current route-record sample size: 377 rows over 1,658 deduplicated
cancellation route records. The `post-subresource-cancel` split intentionally
spends more reviewer effort on unlinked records, where operation-vs-domain
semantics cannot be inferred from structure alone.

## Current Family-Pattern Support Strata

Rows are non-exclusive pattern-family memberships. Do not compare the sum of
membership rows to the 407 unique strict cancellation families. The membership
sum is valid only as the 517-row sampling-frame size for the support
pattern-family sheet. Sampling fractions intentionally vary by stratum, so a raw
pooled TP rate from the 260 rows is invalid.

| Pattern | Population family memberships | Same-resource linked families | Operation target families | Domain-transition-risk families | Sampled representatives | Sampling fraction | Estimation population |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `post-subresource-cancel` | 330 | 155 | 180 | 242 | 80 | 24.2% | strict cancellation |
| `post-action-cancel` | 106 | 31 | 35 | 80 | 50 | 47.2% | strict cancellation |
| `delete-action-cancel` | 31 | 19 | 24 | 8 | 30 | 96.8% | strict cancellation |
| `put-action-cancel` | 27 | 7 | 10 | 21 | 27 | 100.0% | strict cancellation |
| `get-cancel-link` | 18 | 4 | 5 | 15 | 18 | 100.0% | strict cancellation |
| `patch-state-cancelled` | 5 | 1 | 2 | 3 | 5 | 100.0% | strict cancellation |
| `delete-operation-resource` | 209 | 185 | 202 | 0 | 50 | 23.9% | promotion audit |

Total proposed sample size: 260 family-pattern representative rows. The strict
sample is 210 rows drawn from 517 strict pattern-family memberships. The
`delete-operation-resource` audit is 50 rows drawn from a separate 209-membership
population.

For `delete-operation-resource`, use the 185/209 same-resource linkage as the
reason to sample the bucket. Do not treat 202/209 operation-like target or zero
domain-transition risk as independent evidence of precision.

If reviewer time is constrained, use a 140-row minimum pattern-family sample:

| Pattern | Minimum sample |
| --- | ---: |
| `post-subresource-cancel` | 50 |
| `post-action-cancel` | 30 |
| `delete-action-cancel` | 20 |
| `put-action-cancel` | 15 |
| `get-cancel-link` | 10 |
| `patch-state-cancelled` | 5 |
| `delete-operation-resource` | 10 |

## Unique-Family Denominator Sample

The pattern-family sheet must not be used to update the 407-family denominator,
because a family with multiple strict patterns has multiple chances to be
sampled and may be more likely to be a true operation-cancellation API.

Generate a separate unique-family sheet before making claims over the 407 strict
cancellation families:

```bash
rfc-miner sample-cancellation-family \
  --data-dir /mnt/cash-data/rfc-http-miner/data-5000-refined \
  --profile full
```

Current generated snapshot:

| Sheet | Population | Sample | Sampling fraction | Use |
| --- | ---: | ---: | ---: | --- |
| `docs/validation/http-cancellation-family-sample-2026-09-04.csv` | 407 strict families | 140 families | 34.4% | update unique-family claims |

Use this sheet, not the pattern-family sheet, when updating the 407 / 194 / 222
family-level claims. The family-level primary label means: this family exposes
at least one true operation-cancellation affordance among its strict cancellation
evidence.

The pattern-family sheet includes an exploratory
`strictFamilyApproxInclusionProbability` column using:

```text
pi_family ≈ 1 - product(1 - f_pattern)
```

where `f_pattern` is the observed sampling fraction for each strict pattern
present in that family. Treat this only as a sensitivity check: bucket quotas and
repository caps make the exact design probability more complex than the simple
formula.

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

The current pattern-family representative design satisfies the anti-domination
requirement for each pattern stratum: a single repository/family can contribute
at most one row to a given pattern before repository caps are applied.

The route-record sheet intentionally does not apply those family caps because
it estimates a route-record population with known stratum inclusion
probabilities. Report repository concentration for route-record labels
separately, and do not translate route-record precision into family prevalence.

## Linkage Sub-Strata

Within each pattern, sample across route-level buckets when available:

- same-resource async linked;
- operation-like target without same-resource linkage;
- domain-transition risk;
- mixed same-resource/risk or operation-target/risk, where one family-pattern
  contains both operation-looking and domain-looking cancellation records.

For the route-record sheet, split `post-subresource-cancel` into linked and
unlinked strata. The full profile samples 30 linked records and 70 unlinked
records, because the unlinked side contains most of the domain-transition-risk
work.

For small strata, include all available representative rows and mark the missing linkage
buckets as empty rather than oversampling another bucket without notation.

## Labels

Use exactly one primary label:

- `operation-cancellation`: the canceled target is an observable operation, job,
  task, run, execution, workflow, build, deployment, pipeline, export, import,
  backup, restore, sync, scan, render, transcode, training, migration, index,
  provision, snapshot, report, query, status monitor, or equivalent operation
  handle.
- `domain-state-transition`: the canceled target is a business object such as a
  subscription, order, booking, plan, invoice, reservation, request, account, or
  membership. Decide this from operation summaries, response schemas, lifecycle
  fields, repository documentation, and creation responses, not from automated
  linkage fields.
- `ambiguous`: the route suggests cancellation, but the available route,
  operation name, response codes, and adjacent paths do not prove whether the
  target is an operation or a business object.

Use secondary flags when applicable:

- `extractor_false_positive`: the route was not a server-side HTTP API route or
  was classified from unrelated text.
- `generated_duplicate`: the record appears to be generated from a copied
  catalog or repeated spec source.
- `mixed_family_pattern`: the sampled family-pattern contains both
  operation-looking and domain-looking cancellation routes.
- `needs_adjacent_context`: the label depends on nearby routes not included in
  the sampled representative row.

Blind-labeling rule:

- Hide `routeStratum`, `linkageBucket`, `familyPatternHas*`,
  `strictFamilyHas*`, `routeLevelOperationLinked`, `operationTarget`,
  `domainTransitionRisk`, and precomputed adjacent-linkage evidence from human
  labelers during the first pass.
- Allow each labeler the same bounded context budget: the sampled route,
  operation summary/name, response codes and schema, nearby lifecycle/status
  routes found by manual inspection, repository README/API docs when present,
  and whether creation of the target resource returns `202` or an operation
  handle.
- Unhide automated linkage fields only after independent labels are recorded,
  then use them for estimator weights, disagreement analysis, and extractor
  improvement.

## Label Sheet Columns

The route-record sheet adds these route-frame fields:

- `routeStratum`
- `routeFramePopulationRecords`
- `routeStratumSampleSize`
- `routeStratumSamplingFraction`
- `routeStratumAnalysisWeight`

The support pattern-family sheet uses these pattern-frame fields:

- `sample_id`
- `samplingUnit`
- `estimationPopulation`
- `family_id`
- `repository`
- `pattern`
- `linkageBucket`
- `populationFamilyMemberships`
- `patternSampleSize`
- `patternSamplingFraction`
- `analysisWeight`
- `familyPatternHasSameResourceLinked`
- `familyPatternHasOperationTarget`
- `familyPatternHasDomainTransitionRisk`
- `familyPatternCancellationEvidence`
- `strictFamilyPatternMemberships`
- `strictFamilyApproxInclusionProbability`
- `strictFamilyApproxAnalysisWeight`

All sheets share these route/context and label columns:

- `family_id`
- `repository`
- `pattern`
- `httpMethod`
- `normalizedPath`
- `path`
- `sourceKind`
- `file`
- `lineStart`
- `commit`
- `symbol`
- `responseCodes`
- `confidence`
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

The strict-family sheet uses the same route/context label columns, but replaces
pattern-frame fields with:

- `populationStrictFamilies`
- `strictFamilySampleSize`
- `strictFamilySamplingFraction`
- `strictFamilyAnalysisWeight`
- `strictFamilyPatternMemberships`
- `strictFamilyHasSameResourceLinked`
- `strictFamilyHasOperationTarget`
- `strictFamilyHasDomainTransitionRisk`
- `strictFamilyCancellationEvidence`

For the route-record sheet, the primary label applies only to the sampled route
record. Use route-frame weights for route-record precision and do not infer that
all routes in the same family have the same semantics.

For the pattern-family sheet, the primary label applies to the representative
row. It is not a claim that every cancellation route in the same family-pattern
membership has the same semantics. For mixed buckets, inspect
`familyPatternCancellationEvidence` only after the first blind pass and use the
`mixed_family_pattern` secondary flag when both operation and domain
cancellation are present. If within-family mixing prevalence matters, run a
follow-up all-routes audit on mixed buckets; the representative-row sheet is not
designed to estimate that prevalence.

For the strict-family sheet, the primary label applies to the family: label
`operation-cancellation` if any strict cancellation evidence in the family is a
true operation-cancellation affordance. Inspect `strictFamilyCancellationEvidence`
only after the first blind pass.

Recommended `reviewerConfidence` values:

- `high`: route and independent context clearly identify the target semantics;
- `medium`: route semantics are likely but missing one supporting signal;
- `low`: label relies on naming only.

## Review Process

1. Generate the route-record, pattern-family, and strict-family sheets from the
   same normalized evidence and family data.
2. Give two reviewers a blinded copy of the selected sheet. Hide automated
   linkage fields and each other's labels.
3. Require both reviewers to use the same bounded context budget and to record
   the independent evidence they used in `rationale`.
4. Measure raw agreement and Cohen's kappa before discussion.
5. Adjudicate disagreements into `adjudicatedLabel` with a third pass or named
   adjudicator.
6. Record common false-positive causes and update extractor or linkage rules
   only after adjudication.
7. Recompute corrected prevalence from adjudicated labels using the estimators
   below.

Agreement metrics:

- report raw agreement by label;
- report Cohen's kappa if both reviewers complete the same sample;
- list all representative rows where one reviewer chose
  `operation-cancellation` and the other chose `domain-state-transition`.

## TP Rate and Confidence Intervals

For each route or pattern stratum, compute these three ambiguity-safe rates:

- `n`: adjudicated sample size;
- `N`: population units for the stratum (`routeFramePopulationRecords` for the
  route sheet, `populationFamilyMemberships` for the support pattern sheet);
- `tp`: rows labeled `operation-cancellation`;
- `ambiguous`: rows labeled `ambiguous`;
- `ambiguous_as_fp_rate`: `tp / n`;
- `ambiguous_excluded_rate`: `tp / (n - ambiguous)` when
  `n - ambiguous > 0`;
- `ambiguous_as_tp_rate`: `(tp + ambiguous) / n`.

Report Wilson or Clopper-Pearson 95% confidence intervals for sampled strata. Do
not use Wald intervals for small strata such as `n=5`, `n=18`, or `n=27`. When a
stratum is a full census (`n == N`), mark it as census and do not present a
sampling-error interval as if it were sampled. For near-census strata such as
`delete-action-cancel` (`30/31`), apply a finite-population correction when
estimating sampling variance.

Wilson interval:

```text
center = (p + z²/(2n)) / (1 + z²/n)
margin = z * sqrt((p(1-p) + z²/(4n)) / n) / (1 + z²/n)
z = 1.96
```

For the primary route-record estimate, use the route sheet:

```text
route_weighted_rate = sum(N_route_stratum * rate_route_stratum) / sum(N_route_stratum)
```

The route strata are exclusive in this sheet. Compute the route-weighted
estimate separately for `ambiguous_as_fp_rate`, `ambiguous_excluded_rate`, and
`ambiguous_as_tp_rate`. Its denominator is 1,658 deduplicated cancellation route
records, not 407 unique strict families and not 517 strict pattern-family
memberships.

For the support strict cancellation estimate, use a stratified pattern-family
weighted estimate over the strict patterns only:

```text
pattern_weighted_rate = sum(N_pattern * rate_pattern) / sum(N_pattern)
```

Compute the weighted estimate separately for `ambiguous_as_fp_rate`,
`ambiguous_excluded_rate`, and `ambiguous_as_tp_rate`. This denominator is the
517 strict pattern-family memberships, not the 407 unique strict cancellation
families. Its sampling variance should use stratum weights and finite-population
correction; in practice the non-census contribution is dominated by
`post-subresource-cancel` and `post-action-cancel`.

Use the strict-family sheet for the 407-family estimate:

```text
family_rate = labeled_operation_cancellation_families / sampled_strict_families
```

The current full sheet is a simple random sample of 140 out of 407 strict
families. Apply finite-population correction to its interval and report labeling
disagreement separately.

Report separate estimates for:

- route-record cancellation precision;
- strict cancellation only;
- strict same-resource linked cancellation;
- strict operation-like target cancellation;
- `delete-operation-resource` audit evidence.

Do not combine `delete-operation-resource` into the strict denominator unless
the adjudicated sample justifies changing the strict definition.

## Acceptance Thresholds For Drafting

Proceed to an Internet-Draft skeleton if:

- route-record TP rates and the route-weighted operation-cancellation estimate
  are published with ambiguity bounds, confidence intervals, finite-population
  correction where applicable, and denominator caveats;
- `post-subresource-cancel` linked and unlinked route strata are reported
  separately so business-cancellation precision risk is visible;
- per-pattern TP rates and the support strict pattern-family estimate are
  published as secondary evidence, not as a family prevalence denominator;
- the strict-family sample is labeled before updating unique-family denominator
  claims over 407 / 194 / 222 families;
- domain-state-transition examples are explicitly acknowledged in the
  motivation;
- `delete-operation-resource` is either kept as supporting evidence or promoted
  through a documented rule change.

If these conditions fail, keep `http-cancellation` as a section of the broader
operation-resource study rather than a standalone draft.
