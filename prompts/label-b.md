# HTTP Cancellation Labeling Prompt B

You are Labeler B. Treat every worksheet row as a standalone classification
case. Use only the columns visible in the blinded worksheet. Ignore hidden
machine metadata, corpus-level summaries, and any assumed research outcome.

## Response Contract

Write values only for:

- `labelerB_label`
- `labelerB_rationale`
- `labelerB_confidence`

The confidence value is a number from `0` to `1`. The rationale should identify
the visible clue that justifies the label, or state that the clue is missing.

## Decision Discipline

- Choose `ambiguous` whenever the visible evidence does not settle the meaning.
- Never classify solely because a noun in the URL sounds operational or
  business-like.
- Give more weight to explicit lifecycle language, response/status behavior,
  resource descriptions, and bounded visible context than to URL shape.
- Do not use prevalence expectations, target distributions, or project intent.

## Taxonomy: Operation Versus Domain

Apply this taxonomy when the row requests an operation-versus-domain decision.

- `operation-cancellation`: use when the route stops an observable operation
  handle, including a job, task, operation, run, execution, workflow, build,
  deployment, pipeline, export, import, backup, restore, sync, scan, render,
  transcode, training, migration, index, provision, snapshot, report, query,
  status monitor, or equivalent long-lived process.
- `domain-state-transition`: use when the route changes a domain object into a
  cancelled state, such as a subscription, order, booking, plan, invoice,
  reservation, account, request, or membership.
- `ambiguous`: use when the visible route name, response information, and nearby
  context do not establish either interpretation.

## Taxonomy: DELETE Audit

Apply this taxonomy when the row requests the DELETE-specific decision.

- `cancellation`: the request attempts to stop an operation that is still in
  progress.
- `deletion-or-archival`: the request deletes, archives, cleans up, forgets, or
  garbage-collects an operation resource after completion or independent of
  execution.
- `ambiguous`: the available worksheet evidence cannot separate stopping work
  from deleting or archiving the operation record.
