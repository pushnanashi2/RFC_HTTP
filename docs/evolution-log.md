# Evolution Log

This log records why extraction and analysis logic changes over time.

## 2026-09-04 — Initial vertical slice

- problem: No reproducible OSS measurement system existed for RFC candidate discovery.
- observed failure: Manual LLM review would produce opaque classifications without corpus-level evidence.
- root cause: The project lacked staged data artifacts, explicit evidence schema, and deterministic extractors.
- change: Added research design, architecture, evidence-first CLI pipeline, OpenAPI/source-route extractors, normalization, deduplication, clustering, standards comparison, scoring, reporting, and fixture regressions.
- expected effect: HTTP async-operation and cancellation patterns can be measured across a pinned corpus and traced back to code locations.
- actual effect: Pending first real corpus run.
- regression added: Fixture tests cover OpenAPI extraction, source route extraction, normalization, deduplication, clustering, scoring, and CLI pipeline execution.

## 2026-09-04 — Source route context narrowed

- problem: Source-route extraction could classify a route using cancellation words from a neighboring handler.
- observed failure: The fixture `POST /jobs` and `GET /jobs/:jobId/status` were incorrectly classified as cancellation because the text window included `cancelJob`.
- root cause: The extractor used a broad byte window around a route match rather than a route-local handler context.
- change: Replaced broad nearby text with a route-local context that stops at the apparent handler boundary and uses that same context for response-code extraction.
- expected effect: Adjacent handlers no longer leak cancellation/status terms into unrelated routes.
- actual effect: Pending rerun.
- regression added: Existing fixture pipeline asserts the expected cancellation and async patterns after context narrowing.

## 2026-09-04 — Streaming corpus run mode

- problem: Stage-1 execution could fill the local disk because `run` collected all repository checkouts before analysis.
- observed failure: A 30-repository run exhausted available disk space and a single clone failure stopped the full corpus.
- root cause: Collection and analysis were separated inside the one-shot `run` command, so large shallow clones accumulated before evidence extraction; the default checkout path also used the small root disk unless overridden.
- change: Added streaming collection/analyze mode for `run`, clone-error capture, cleanup of partial checkouts, and `RFC_MINER_REPO_DIR` / `RFC_MINER_DATA_DIR` storage overrides.
- expected effect: Real corpus runs continue across individual clone failures and keep only one checkout on disk by default.
- actual effect: A 30-repository Stage-1 run completed with zero extraction errors while leaving `data/repos` empty after checkout cleanup.
- regression added: Existing CLI fixture pipeline exercises the streaming-compatible downstream stages; real corpus run will validate cleanup behavior.

## 2026-09-04 — Stage-1 false-positive reduction

- problem: The first 30-repository run included test, mock, and fixture route calls as implementation evidence and treated some GET/DELETE routes too broadly as cancellation or async operation evidence.
- observed failure: Airflow unit tests, UI mock handlers, and generic workflow deletion routes appeared in cancellation and async-operation aggregates.
- root cause: Source-route extraction scanned test-like directories, GET async classification used context-only nouns, and DELETE cancellation accepted broad async nouns such as workflow.
- change: Source-route extraction now ignores relative test/mock/fixture/example/doc directories, tokenization handles camelCase route terms, GET async requires an async noun in the path, and DELETE cancellation is restricted to operation-instance nouns.
- expected effect: Stage-1 prevalence remains evidence-backed while reducing test/mock pollution and workflow-definition false positives.
- actual effect: Stage-1 evidence dropped from 6,093 noisy records to 2,124 async-operation and 159 cancellation records before the strong-cancellation refinement.
- regression added: Fixture source-route test verifies routes under a relative `tests/` directory are ignored.

## 2026-09-04 — Strong cancellation evidence

- problem: Cancellation detection still accepted weak cancellation words from broad operation text and left common PUT/GET cancellation forms as `other-cancellation-route`.
- observed failure: Generic routes with cancellation wording in surrounding text could be classified, while Argo `PUT /workflows/{name}/stop` and Windmill signed GET cancel links lacked specific patterns.
- root cause: The classifier did not distinguish strong path or operation-name evidence from incidental text evidence, and pattern definitions lacked PUT/GET cancellation forms.
- change: Cancellation now requires a cancellation word in the path or operation/handler name, POST async classification ignores query/list/count paths without stronger evidence, and cancellation patterns include `put-action-cancel` and `get-cancel-link`.
- expected effect: Fewer incidental cancellation false positives and more informative clustering of non-POST cancellation variants.
- actual effect: The final 30-repository Stage-1 run produced 1,907 async-operation records, 138 cancellation records, zero `other-*` pattern buckets, and zero extraction errors.
- regression added: Tests cover GET incidental cancellation text rejection and PUT stop-route pattern assignment.

## 2026-09-04 — Large corpus discovery command

- problem: The initial implementation only had a fixed 30-repository Stage-1 seed, so it could not directly execute a 5,000-repository corpus.
- observed failure: A request for 5,000 repositories was answered with a 30-repository run.
- root cause: Corpus discovery was manual/static instead of generated from GitHub Search shards.
- change: Added `discover-github`, a resumable GitHub Search API collector that generates large seed files with language/keyword shards and repository metadata.
- expected effect: Large corpus runs can start from a reproducible 5,000-repository seed rather than hand-written fixtures.
- actual effect: A 50-repository smoke discovery completed, but exposed SDK/client-heavy results from broad OpenAPI queries.
- regression added: Discovery tests cover query generation and seed conversion.

## 2026-09-04 — Streaming run resume support

- problem: A 5,000-repository corpus run can be interrupted by network, time, or disk pressure and should not restart from zero.
- observed failure: The initial streaming mode persisted after each repository but did not skip already processed repositories on rerun.
- root cause: Streaming execution always initialized in-memory repositories, evidence, and errors as empty lists.
- change: Streaming mode now loads existing stage outputs by default, skips processed repo IDs, prints per-repository progress, and supports `--fresh` for intentional overwrite.
- expected effect: Long 5,000-repository runs can be resumed with the same command.
- actual effect: A 5,000-repository run began and was safely interrupted after six repositories, then prepared for parallel resume.
- regression added: Existing CLI tests cover command parsing; corpus resume behavior was smoke-tested with two repositories.

## 2026-09-04 — Parallel streaming execution

- problem: Sequential streaming would take too long for 5,000 repository analysis.
- observed failure: The first 5,000-repository run processed only a few repositories in the first minute.
- root cause: Clone and extraction were serialized even though repositories are independent units of work.
- change: Added `--jobs` / `RFC_MINER_JOBS` parallel repository workers while preserving seed-order output writes, configurable flush intervals, and per-repository progress logging.
- expected effect: Large corpus runs complete materially faster without keeping thousands of checkouts.
- actual effect: 5,000-repository execution resumed safely from the previous checkpoint; 12-way parallelism is used for the external SSD run.
- regression added: Resume smoke test validates rerunning the same seed does not duplicate repository records.

## 2026-09-04 — SDK-only discovery filtering

- problem: Broad `openapi` / `swagger` discovery queries returned generated SDKs and API clients that do not provide independent server-side HTTP interaction implementations.
- observed failure: The first discovery smoke sample included repositories such as API clients and OpenAPI helper libraries.
- root cause: Discovery accepted search hits based on terms alone instead of requiring server-like metadata and rejecting SDK-only metadata.
- change: Reordered default query terms toward workflow/orchestration/server concepts and added deterministic metadata filters for SDK/client-only, toy, template, tutorial, prompt-pack, editor-extension, GitHub Action, CLI-only, and over-large candidates.
- expected effect: The 5,000-repository seed is biased toward API server and orchestration implementations rather than generated-client ecosystems.
- actual effect: A filtered 5,000-repository seed was generated on external storage with zero `awesome`, `template`, `sample`, `example`, `prompt`, `github-action`, `obsidian`, `comfyui`, or `sdk` substring hits in the seed inspection.
- regression added: Discovery tests verify SDK-only candidates are excluded and server-like candidates are retained.

## 2026-09-04 — Balanced large-corpus discovery

- problem: The first 5,000-repository discovery reached the target before later languages were searched.
- observed failure: A sequential language-first query order produced a seed dominated by Go, TypeScript, and Python.
- root cause: Query generation iterated all terms for one language before moving to the next language.
- change: Discovery now interleaves query shards by term and language, adds a configurable GitHub repository size cap, and stores `size_kb` in seed records.
- expected effect: Early target stops still include all configured implementation languages.
- actual effect: The regenerated 5,000-repository seed spans Go, TypeScript, Python, JavaScript, Rust, Java, C#, PHP, Ruby, Kotlin, Elixir, and Scala.
- regression added: Discovery tests assert interleaved query order and the size-qualified GitHub Search query.

## 2026-09-04 — Large-corpus clone trimming

- problem: Full default clone behavior wastes bandwidth for large corpus analysis.
- observed failure: The 5,000-repository run was network-bound even with checkout cleanup enabled.
- root cause: Shallow clones still fetched tags and did not force single-branch fetches.
- change: Collection now uses shallow, single-branch, tagless clones for uncached repositories.
- expected effect: The 5,000-repository corpus run spends less time and bandwidth on irrelevant Git metadata.
- actual effect: The 5,000-repository external SSD run restarted with the trimmed clone command.
- regression added: Collector tests assert `--depth`, `--single-branch`, and `--no-tags` are used for fresh clones.

## 2026-09-04 — Final 5,000-repository external SSD run

- problem: The initial 5,000-repository run surfaced extractor and normalization weaknesses that were invisible in the 30-repository corpus.
- observed failure: Permission-denied files produced duplicate analysis errors, client-side `api.delete(...)` calls were treated as server routes, decorator routes could inherit the previous handler symbol, and `{repo_id:path}` normalized to an invalid extra-brace path.
- root cause: Repository walking used `Path.rglob` without safe file checks, source-route regexes were not scoped by language/receiver, decorator symbols were searched backward, and colon-style parameters were normalized before brace parameters.
- change: Added safe filesystem walking, language-scoped route regexes, client-call and test-file exclusion, forward handler lookup for decorators, typed-brace path normalization, and report-level evidence concentration metrics.
- expected effect: Large corpus runs complete with fewer false positives and expose generated-spec concentration rather than hiding it in raw evidence counts.
- actual effect: The final run processed 5,000 repositories, found 4,994 independent implementation families, extracted 24,647 evidence records, recorded zero extraction errors, and produced two RFC candidates: `http-async-operation` and `http-cancellation`, both scoring 68.
- regression added: Tests now cover unreadable repository entries, client-call/test-file skipping, decorator handler attribution, typed brace path normalization, discovery filtering, balanced discovery order, shallow clone flags, and streaming resume.

## 2026-09-04 — Refined evidence aggregation and strict scoring

- problem: Raw evidence counts were inflated by repeated generated OpenAPI catalogs, and broad async/cancellation heuristics made the RFC candidate ranking harder to trust.
- observed failure: The 5,000-repository analysis showed that generated specs could dominate raw evidence volume and that `delete-operation-resource` was weaker than explicit cancellation actions.
- root cause: Normalization preserved every matching file-level record even when the same repository repeated the same concept, method, normalized path, and source kind; scoring exposed only the broad score.
- change: Normalized evidence is now deduplicated by repository, concept, method, normalized path, and source kind; score output now includes strict-mode counts and strict scores; Markdown reports label raw versus deduplicated evidence.
- expected effect: RFC triage relies more on independent families and strong interaction patterns, while raw evidence remains available for extractor-volume diagnostics.
- actual effect: The refined 5,000-repository run processed 5,000 repositories, found 4,993 independent families, extracted 24,914 raw evidence records, reduced them to 14,004 deduplicated evidence records, and recorded zero extraction errors. `http-cancellation` ranked first with score 69 and strict score 67; `http-async-operation` scored 68 with strict score 67.
- regression added: Tests cover repository/source-kind deduplication, strict score fields, and report rendering of strict scores.

## 2026-09-04 — Framework-specific route extraction expansion

- problem: Deterministic source extraction missed common server routes in ASP.NET minimal APIs, Laravel route files, and Phoenix routers.
- observed failure: Review identified missed relative Laravel paths, handler-name cancellation such as `MapPut("/tasks/{id}", CancelTask)`, and Phoenix scope prefixes.
- root cause: Source-route patterns did not model these framework route declarations, and inline route actions were not used as operation names.
- change: Added ASP.NET `MapGet/Post/Put/Patch/Delete`, ASP.NET `MapGroup` prefix recovery, Laravel `Route::` declarations with `Route::prefix`, Phoenix router routes with `scope`, and inline handler/action symbol extraction.
- expected effect: Server-side route evidence increases for C#, PHP, and Elixir without admitting generic client calls.
- actual effect: The refined 5,000-repository run found 216 Laravel route records across 20 repositories, 30 Phoenix route records across 3 repositories, and 18 ASP.NET minimal API records across 5 repositories.
- regression added: Tests cover ASP.NET grouped routes, Laravel relative/prefixed routes, handler-name cancellation, Phoenix scope prefixes, and non-router Elixir client-call rejection.

## 2026-09-04 — Cancellation-first draft framing

- problem: The first analysis framed cancellation primarily as narrower and less covered, which underweighted the strongest IETF argument.
- observed failure: Review noted that the corpus already shows convergence on `POST /.../{id}/cancel`, so the missing piece is semantics rather than endpoint shape.
- root cause: The analysis treated async overlap mostly as composability evidence and did not foreground the counterargument that cancellation could be an operation-resource affordance.
- change: Reframed the analysis around de facto shape convergence, added denominator caveats, labeled pattern counts as memberships, added a prior-art matrix, and created a cancellation-first Internet-Draft outline.
- expected effect: The next draft pitch can argue for standardizing observed semantics without overstating prevalence or proposing a new route shape.
- actual effect: The current recommendation is to validate TP/FP samples first, then pursue `http-cancellation` as either a standalone cancellation profile or a section in a broader operation-resource draft.
- regression added: Documentation now links the refined 5,000-repository results to prior art and a concrete draft outline.

## 2026-09-04 — Route-level cancellation precision correction

- problem: Repository/family-level async overlap made business-domain cancellation look like long-running operation cancellation.
- observed failure: A repository with `/jobs/{id}/status` and `/subscriptions/{id}/cancel` could count as async-overlapping cancellation even though the cancel route targets a different resource.
- root cause: The analysis joined concepts at repository/family scope instead of checking whether a cancel target maps to the same normalized operation resource as status/progress/result evidence.
- change: Added route-level cancellation linkage metrics, operation-like target detection, and domain-transition-risk counts to candidate reports.
- expected effect: Internet-Draft motivation uses a defensible operation-cancellation subset rather than raw `POST /.../{id}/cancel` shape counts.
- actual effect: The refined 5,000-repository run now reports 407 strict cancellation families, 194 same-resource linked strict families, 215 operation-like-target strict families, and 302 strict families with at least one domain-transition-risk route.
- regression added: Tests verify that same-repository async evidence does not link an unrelated business cancellation route.

## 2026-09-04 — Cancellation sampling protocol

- problem: The analysis still mixed denominators in prose and did not define a repeatable manual labeling plan.
- observed failure: Readers could confuse `/407` strict-cancellation ratios with `/631` async-family ratios, add non-exclusive pattern rows, or miss why the highly linked `delete-operation-resource` bucket stayed outside strict scoring.
- root cause: The report exposed corrected metrics without a denominator-safe presentation or a pattern/repository-stratified validation protocol.
- change: Rewrote the analysis ratios as denominator-explicit tables, repeated the non-exclusive membership warning in pattern tables, documented the `delete-operation-resource` tradeoff, and added a sampling protocol with pattern sample sizes, repository caps, labels, adjudication, and Wilson confidence intervals.
- expected effect: The next validation pass can produce publishable TP-rate estimates without letting business cancellation or one large catalog dominate the sample.
- actual effect: Internet-Draft drafting remains gated on manual operation-cancellation vs domain-state-transition sampling; `delete-operation-resource` is now described as definition-independent only for same-resource linkage, not for operation-like-target or zero-risk counts.
- regression added: Generated candidate reports now include denominator-safe route-level linkage ratios, a risk-queue row, and non-exclusive pattern membership warnings.

## 2026-09-04 — Cancellation validation sample generation

- problem: The sampling protocol was documented but not executable, so the next validation step still depended on ad hoc spreadsheet construction.
- observed failure: A reviewer could not reproduce the exact pattern mix, linkage buckets, repository caps, or blank label columns from the protocol alone.
- root cause: Route-level linkage existed only as aggregate report data and was not reusable as per-record sampling metadata.
- change: Added a deterministic `sample-cancellation` command that emits a CSV label sheet and summary JSON from normalized evidence and family data.
- expected effect: Reviewers can label the same sample sheet and compute TP rates without redoing corpus extraction.
- actual effect: The 5,000-repository run produced a 260-row unlabeled family-pattern representative sample with all protocol strata filled: 80 `post-subresource-cancel`, 50 `post-action-cancel`, 30 `delete-action-cancel`, 27 `put-action-cancel`, 18 `get-cancel-link`, 5 `patch-state-cancelled`, and 50 `delete-operation-resource`.
- regression added: Tests verify sample-sheet generation preserves same-resource-linked and domain-transition-risk buckets with blank labels.

## 2026-09-04 — Cancellation sample estimator hardening

- problem: The generated sample sheet could be misused as a raw record-level pool even though sample fractions differ sharply by pattern.
- observed failure: A family-pattern with multiple cancellation routes could appear more than once, and `delete-operation-resource` could be accidentally mixed into the strict TP estimate.
- root cause: The sheet did not make the sampling unit, estimation population, weighting, or ambiguous-label handling explicit enough for external review.
- change: Sample generation now emits one representative per `family_id` × `pattern`, adds population counts, sampling fractions, analysis weights, and separates strict cancellation from `delete-operation-resource` promotion audit rows.
- expected effect: Labeling produces per-pattern rates and a strict pattern-family weighted estimate rather than an invalid pooled TP rate.
- actual effect: The protocol now requires ambiguity bounds, Wilson or Clopper-Pearson intervals, census-stratum handling, two blind reviewers, agreement reporting, and adjudication before drafting.
- regression added: Tests verify sample rows are unique by `family_id` × `pattern` and carry estimator metadata.
