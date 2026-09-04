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

- one `family_id` × `pattern` membership, represented by the highest-quality
  evidence record for that membership.
- the sheet must not contain two rows with the same `family_id` and `pattern`.
- this estimates pattern-family membership precision. It does not estimate
  route-record precision or unique-family prevalence over the 407 strict
  cancellation families.

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
Sampling fractions intentionally vary by stratum, so a raw pooled TP rate from
the 260 rows is invalid.

| Pattern | Population family memberships | Same-resource linked families | Operation target families | Domain-transition-risk families | Sampled representatives | Sampling fraction | Estimation population |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `post-subresource-cancel` | 330 | 155 | 173 | 246 | 80 | 24.2% | strict cancellation |
| `post-action-cancel` | 106 | 31 | 34 | 80 | 50 | 47.2% | strict cancellation |
| `delete-action-cancel` | 31 | 19 | 24 | 8 | 30 | 96.8% | strict cancellation |
| `put-action-cancel` | 27 | 7 | 10 | 21 | 27 | 100.0% | strict cancellation |
| `get-cancel-link` | 18 | 4 | 4 | 16 | 18 | 100.0% | strict cancellation |
| `patch-state-cancelled` | 5 | 1 | 2 | 3 | 5 | 100.0% | strict cancellation |
| `delete-operation-resource` | 209 | 185 | 202 | 0 | 50 | 23.9% | promotion audit |

Total proposed sample size: 260 family-pattern representative rows. The strict
sample is 210 rows drawn from 517 strict pattern-family memberships. The
`delete-operation-resource` audit is 50 rows drawn from a separate 209-membership
population.

For `delete-operation-resource`, use the 185/209 same-resource linkage as the
reason to sample the bucket. Do not treat 202/209 operation-like target or zero
domain-transition risk as independent evidence of precision.

If reviewer time is constrained, use a 140-row minimum sample:

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

Within each pattern, sample across route-level buckets when available:

- same-resource async linked;
- operation-like target without same-resource linkage;
- domain-transition risk.
- mixed same-resource/risk or operation-target/risk, where one family-pattern
  contains both operation-looking and domain-looking cancellation records.

For `post-subresource-cancel`, prefer roughly balanced thirds across the three
buckets because it is both the dominant shape and the largest precision risk.

For small strata, include all available representative rows and mark the missing linkage
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
- `mixed_family_pattern`: the sampled family-pattern contains both
  operation-looking and domain-looking cancellation routes.
- `needs_adjacent_context`: the label depends on nearby routes not included in
  the sampled representative row.

## Label Sheet Columns

Required columns:

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

The primary label applies to the representative row. It is not a claim that
every cancellation route in the same family-pattern membership has the same
semantics. For mixed buckets, inspect `familyPatternCancellationEvidence` and use
the `mixed_family_pattern` secondary flag when both operation and domain
cancellation are present.

Recommended `reviewerConfidence` values:

- `high`: route and adjacent evidence clearly identify the target semantics;
- `medium`: route semantics are likely but missing one supporting signal;
- `low`: label relies on naming only.

## Review Process

1. Generate the sample sheet from normalized evidence and family data.
2. Two reviewers label each representative row independently and blind to each
   other's labels.
3. Measure raw agreement and Cohen's kappa before discussion.
4. Adjudicate disagreements into `adjudicatedLabel` with a third pass or named
   adjudicator.
5. Record common false-positive causes and update extractor or linkage rules
   only after adjudication.
6. Recompute corrected prevalence from adjudicated labels using the estimators
   below.

Agreement metrics:

- report raw agreement by label;
- report Cohen's kappa if both reviewers complete the same sample;
- list all representative rows where one reviewer chose
  `operation-cancellation` and the other chose `domain-state-transition`.

## TP Rate and Confidence Intervals

For each pattern stratum, compute these three ambiguity-safe rates:

- `n`: adjudicated sample size;
- `N`: population family-pattern memberships for the stratum;
- `tp`: representative rows labeled `operation-cancellation`;
- `ambiguous`: representative rows labeled `ambiguous`;
- `ambiguous_as_fp_rate`: `tp / n`;
- `ambiguous_excluded_rate`: `tp / (n - ambiguous)` when
  `n - ambiguous > 0`;
- `ambiguous_as_tp_rate`: `(tp + ambiguous) / n`.

Report Wilson or Clopper-Pearson 95% confidence intervals. Do not use Wald
intervals for small strata such as `n=5`, `n=18`, or `n=27`. When a stratum is a
full census (`n == N`), mark it as census and do not present a sampling-error
interval as if it were sampled.

Wilson interval:

```text
center = (p + z²/(2n)) / (1 + z²/n)
margin = z * sqrt((p(1-p) + z²/(4n)) / n) / (1 + z²/n)
z = 1.96
```

For the overall strict cancellation estimate, use a stratified pattern-family
weighted estimate over the strict patterns only:

```text
weighted_rate = sum(N_pattern * rate_pattern) / sum(N_pattern)
```

Compute the weighted estimate separately for `ambiguous_as_fp_rate`,
`ambiguous_excluded_rate`, and `ambiguous_as_tp_rate`. This denominator is the
517 strict pattern-family memberships, not the 407 unique strict cancellation
families. If a unique-family prevalence estimate is needed, create a separate
sample whose unit is one strict cancellation family.

Report separate estimates for:

- strict cancellation only;
- strict same-resource linked cancellation;
- strict operation-like target cancellation;
- `delete-operation-resource` audit evidence.

Do not combine `delete-operation-resource` into the strict denominator unless
the adjudicated sample justifies changing the strict definition.

## Acceptance Thresholds For Drafting

Proceed to an Internet-Draft skeleton if:

- `post-subresource-cancel` per-pattern operation-cancellation rate bounds are
  high enough that the dominant-shape argument survives manual review;
- per-pattern TP rates and the weighted strict pattern-family estimate are
  published with ambiguity bounds, confidence intervals, and denominator caveats;
- domain-state-transition examples are explicitly acknowledged in the
  motivation;
- `delete-operation-resource` is either kept as supporting evidence or promoted
  through a documented rule change.

If these conditions fail, keep `http-cancellation` as a section of the broader
operation-resource study rather than a standalone draft.
