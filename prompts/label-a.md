# HTTP Cancellation Labeling Prompt A

You are Labeler A. Label each row independently using only the blinded worksheet
row provided to you. Do not infer from hidden machine columns, repository-wide
aggregate statistics, or the study goal.

## Output Fields

Fill these fields only:

- `labelerA_label`
- `labelerA_rationale`
- `labelerA_confidence`

Use a confidence value from `0` to `1`. Keep the rationale to one concise
sentence grounded in visible evidence.

## General Rules

- If visible evidence is insufficient, choose `ambiguous`.
- Do not decide from path nouns alone.
- Prefer route semantics, response semantics, operation lifecycle wording, and
  bounded visible context over endpoint shape.
- Do not use expected rates, distributions, or any external hypothesis.

## Operation-vs-Domain Taxonomy

Use this taxonomy when the worksheet asks for operation-vs-domain labeling.

- `operation-cancellation`: the route cancels an observable operation, job, task,
  run, execution, workflow, build, deployment, pipeline, export, import, backup,
  restore, sync, scan, render, transcode, training, migration, index, provision,
  snapshot, report, query, status monitor, or equivalent operation handle.
- `domain-state-transition`: the route cancels a business object such as a
  subscription, order, booking, plan, invoice, reservation, account, request, or
  membership.
- `ambiguous`: the visible route, operation name, response semantics, and bounded
  adjacent context do not prove which of the two applies.

## DELETE Audit Taxonomy

Use this taxonomy when the worksheet asks for DELETE audit labeling.

- `cancellation`: the DELETE route requests cancellation of an ongoing operation.
- `deletion-or-archival`: the DELETE route removes, archives, garbage-collects,
  or forgets an operation resource after or independent of execution.
- `ambiguous`: visible evidence does not distinguish cancellation from deletion,
  archival, or garbage collection.
