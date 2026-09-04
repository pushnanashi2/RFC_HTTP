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
