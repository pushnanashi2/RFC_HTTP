# Research Design

## 1. Research Question

Which HTTP API interaction concepts show enough independent implementation
practice, divergence, interoperability value, and standards gaps to justify
standardization work?

This project does not begin by writing an RFC. It builds a repeatable
measurement pipeline that can discover candidate concepts from OSS evidence.

## 2. Scope

The first vertical slice is limited to HTTP APIs and two concepts:

- `http-async-operation`: routes and specifications that create, expose, or
  poll long-running operations, jobs, tasks, runs, workflows, or executions.
- `http-cancellation`: routes and specifications that cancel, abort, stop,
  terminate, kill, or delete an asynchronous operation resource.

Future concepts include idempotency, retry, partial failure, progress, webhooks,
pagination, rate limiting, previews, and lifecycle/deprecation metadata.

## 3. Corpus Selection

Stage 1 uses 20-30 OSS repositories likely to expose HTTP APIs for workflow,
orchestration, job scheduling, developer platform, or cloud-native systems.

Repository records pin the analyzed commit and store:

- `repo_id`
- `repository_url`
- `owner`
- `name`
- `language`
- `framework`
- `stars`
- `forks`
- `license`
- `last_activity`
- `default_branch`
- `commit_hash`
- `project_category`
- `fork_parent`
- `probable_template`
- `probable_origin`
- `vendor`
- `collection_timestamp`

The collector may use GitHub metadata when available, but the commit hash from
the local checkout is the reproducibility anchor.

## 4. Bias / Threats to Validity

- GitHub visibility bias can overrepresent popular or English-language OSS.
- Framework bias can make one framework convention look like ecosystem
  convergence.
- Vendor concentration can inflate a pattern used by one organization.
- OpenAPI-first extraction misses private or undocumented routes.
- Regex and AST-lite route extraction may undercount highly dynamic routing.
- Shallow clones pin the analyzed state but may miss generated artifacts that
  are not committed.
- Same-origin forks, templates, and copied implementations can inflate raw
  repository counts.

Reports must therefore separate raw repository counts from independent
implementation family counts and show language/framework/vendor stratification.
For cancellation, reports must also separate repository/family overlap from
route-level operation linkage so business-domain cancellation does not inflate
long-running-operation cancellation evidence.

## 5. Concept Taxonomy

Initial concepts:

- `http-async-operation`
  - create operation
  - operation status resource
  - polling resource
  - progress resource
- `http-cancellation`
  - action subresource cancellation
  - deletion-as-cancellation
  - state transition cancellation
  - route-level operation cancellation linkage

Concept rules are explicit data/configuration plus deterministic extractors.
LLM suggestions may propose new synonyms or classes, but they are not accepted
until encoded in rules.

## 6. Evidence Model

Every finding is evidence-backed. A downstream aggregate must be traceable to
source evidence with:

- repository and commit
- concept
- evidence type
- HTTP method and path
- response codes when known
- file and line location
- symbol when known
- extracted value
- extractor name and version
- confidence

Aggregate-only outputs are invalid.

## 7. Independent Implementation Definition

The independent implementation family is the unit used for standardization
prevalence. It is not the same as repository count.

Family assignment considers:

- exact Git fork parent
- probable copied project or template origin
- generated SDK indicators
- same API signature across repositories
- organization-level variants

Confidence values are `exact`, `probable`, or `unknown`.

## 8. Extraction Strategy

Extractor precedence:

1. OpenAPI / Swagger JSON
2. OpenAPI / Swagger YAML via deterministic line parser
3. framework-aware route patterns
4. language route patterns
5. deterministic regex
6. documentation parsing
7. LLM-assisted interpretation for review candidates only

The first implementation avoids large language-specific AST stacks and emits a
common intermediate representation. More precise AST extractors can replace
regex extractors behind the same evidence schema.

## 9. Normalization Strategy

Raw strings and semantic classes are separated.

Examples:

- `/jobs/:id/cancel`
- `/jobs/{jobId}/cancel`
- `/jobs/<id>/cancel`

normalize to a shared path shape and then to an interaction pattern such as
`post-subresource-cancel`.

Normalization rules are explicit files under `config/normalization` and
`config/patterns`.

Normalized evidence is deduplicated at repository scope by concept, HTTP method,
normalized path, and source kind. This keeps generated OpenAPI version catalogs
from inflating evidence volume while still retaining separate implementation and
specification sources when both are present.

## 10. Pattern Definition

Patterns are interaction semantics, not just naming similarity.

Examples:

- `post-202-accepted`: `POST` returns `202 Accepted`.
- `post-job-resource`: `POST` creates a job/task/operation-like resource.
- `get-status-resource`: `GET` exposes status/progress.
- `post-subresource-cancel`: `POST /.../{id}/cancel`.
- `delete-operation-resource`: `DELETE /.../{id}` for job/operation-like resources.

Pattern definitions are data-backed and versioned with the extractor.

## 11. Validation Methodology

Each expansion stage creates a manual validation report with:

- true positive examples
- false positive examples
- false negative candidates
- unclassified routes
- extractor errors

Every extractor improvement records:

- problem
- observed failure
- root cause
- change
- expected effect
- actual effect
- regression added

The log is kept in `docs/evolution-log.md`.

## 12. Standards Comparison Methodology

The first standards comparison is a seeded deterministic map, not a semantic
claim that the corpus has been fully compared with all standards.

Initial references include:

- HTTP Semantics (`RFC 9110`)
- Web Linking (`RFC 8288`)
- Link-Template (`RFC 9652`)
- Linkset (`RFC 9264`)
- Prefer Header for HTTP (`RFC 7240`)
- Problem Details (`RFC 9457`)
- HTTP Idempotency-Key Internet-Draft

Coverage values are:

- `full`
- `partial`
- `adjacent`
- `none`
- `unknown`

LLM assistance may summarize gaps, but the structured comparison record stores
the standard, coverage, gap, conflict, evidence, and confidence.

## 13. Scoring Methodology

Scores are 0-100 with visible components:

- Prevalence: 0-20
- Independent implementations: 0-20
- Implementation divergence: 0-20
- Interoperability value: 0-15
- Standards gap: 0-15
- Standards correctness: 0-5
- Specification tractability: 0-5

The score ranks review priority. It does not automatically decide that an RFC
should be written.

Each concept also receives a strict score using the same component model over a
conservative evidence subset:

- `http-async-operation` strict evidence counts `202 Accepted` mutation
  responses and explicit status resources.
- `http-cancellation` strict evidence counts explicit cancellation verbs in the
  route path or operation name, and excludes weak `DELETE` operation-resource
  evidence without cancellation wording.

The strict score is intended to answer “does the RFC candidate survive after
removing broad heuristics?” rather than replace the base score.

For `http-cancellation`, strict scoring is still not sufficient by itself.
Routes such as `POST /subscriptions/{id}/cancel` and
`POST /jobs/{id}/cancel` share the same shape but have different semantics.
Cancellation reports therefore compute route-level operation linkage:

- same-resource async evidence: the cancel target maps to the same normalized
  operation resource as a status/progress/result/operation route in that
  repository;
- operation-like target: the cancel target contains an operation-like noun such
  as job, task, operation, run, execution, workflow, build, deployment, or
  pipeline, export, import, backup, restore, sync, scan, render, transcode,
  training, migration, index, provision, snapshot, report, or query;
- domain-transition risk: a strict cancellation route that has neither of the
  previous properties.

Manual sampling must label cancellation evidence as `operation-cancellation`,
`domain-state-transition`, or `ambiguous` before using corpus prevalence claims
in an Internet-Draft. The current sampling protocol is
`docs/validation/http-cancellation-sampling-protocol.md`.

## 14. Reproducibility Strategy

- Repository commits are pinned at collection time.
- Stage outputs are JSONL or JSON files.
- Each evidence record includes extractor version.
- Each stage can be rerun independently.
- Repository-level failures are saved and do not stop the corpus run.
- Cache directories are stable and can be reused.
- Reports include the input corpus size and output file paths.
