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
