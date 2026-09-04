# HTTP Cancellation Prior Art

Checked on 2026-09-04.

## Summary

The corpus suggests strong convergence on request shape, especially
`POST /.../{id}/cancel`. Existing standards and major vendor guidelines cover
nearby pieces, but they diverge on cancellation semantics:

- whether cancellation is best-effort or guaranteed;
- whether canceling deletes a monitor resource or transitions it to a terminal
  state;
- which status code means “cancellation accepted but not complete”;
- how a client observes the final cancellation result;
- how cancellation interacts with retries and idempotency.

That makes `http-cancellation` a better first Internet-Draft candidate than a
new endpoint-shape proposal. The draft should standardize semantics for an
already-common affordance.

## Prior Art Matrix

| Source | Covered pieces | Cancellation semantics | Gap for this draft |
| --- | --- | --- | --- |
| [RFC 7240 Prefer](https://www.rfc-editor.org/info/rfc7240/) | Defines `Prefer: respond-async` and gives a `202 Accepted` asynchronous response example. | Does not define whether or how the resulting operation can be canceled. It explicitly leaves subsequent result determination implementation-specific. | Good reference for client preference and `202`, but not enough for cancellation lifecycle semantics. |
| [OData v4.0 Protocol, asynchronous requests](https://docs.oasis-open.org/odata/odata/v4.0/os/part1-protocol/odata-v4.0-os-part1-protocol.html#_Toc372793755) | Defines `Prefer: respond-async`, `202 Accepted`, `Location` status monitor, optional `Retry-After`, and status monitor polling. | `DELETE` on the status monitor requests cancellation; `200 OK` or `204 No Content` indicates successful cancellation; `202 Accepted` can mean cancellation itself is asynchronous; unsupported cancellation returns `405`. | Strongest existing precedent, but OData-specific and uses monitor deletion/`404` semantics that do not match all operation-resource practices. |
| [Google AIP-151](https://google.aip.dev/151) and [google.longrunning Operations](https://developers.google.com/optimization/service/reference/rpc/google.longrunning) | Defines a reusable operation object, polling through operations service, metadata, terminal result, and error fields. | `CancelOperation` is best-effort; success is observed later through `GetOperation`; a successfully canceled operation is not deleted and is represented with `Operation.error` code `CANCELLED`. `DeleteOperation` explicitly does not cancel. | Excellent operation-resource model, but RPC-oriented and not directly a generic HTTP endpoint/profile for `POST /.../{id}/cancel`. |
| [Microsoft Azure REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md#long-running-operations--jobs) | Defines LRO initiation, status monitor headers including `operation-location`, polling, operation IDs, and repeatability guidance. | Azure guidance is strong on LRO status resources and retries, but cancellation shape and terminal cancellation semantics are not the uniform center of the guideline. | Useful for polling, `Retry-After`, and idempotency interaction; less directly reusable for cancel affordance semantics. |
| [Microsoft Fabric LRO docs](https://learn.microsoft.com/en-us/rest/api/fabric/articles/long-running-operation) | Uses `202 Accepted`, `Location`, `x-ms-operation-id`, `Retry-After`, status polling, and result retrieval. | Public docs emphasize polling and result retrieval rather than a reusable cancellation contract. | Reinforces operation/status conventions but leaves cancel semantics for this draft to define. |
| [Azure Architecture Center async request-reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply) | Describes `202`, status endpoint polling, `Location`, `Retry-After`, terminal status fields, optional `303`, `Expires`, and idempotency keys. | Recommends exposing `DELETE` on the status endpoint to cancel long-running requests and updating the status resource after back-end cancellation. | Architecture guidance, not a standards-track generic HTTP API profile. |
| [RFC 9457 Problem Details](https://www.rfc-editor.org/info/rfc9457/) | Defines machine-readable HTTP API error details. | Can represent “too late to cancel”, “not cancelable”, or terminal failure details, but does not define the cancellation lifecycle. | Should be referenced for error representation rather than used as the cancellation semantic model. |
| [IETF HTTPAPI WG documents](https://datatracker.ietf.org/wg/httpapi/documents/) | Current active WG items include Byte Range PATCH, RateLimit fields, and REST API Media Types; IESG items include Digest Fields Problem Types and Protecting Credentials with HTTP APIs. | No active HTTPAPI WG document appears to define generic HTTP operation cancellation semantics as of 2026-09-04. | A cancellation profile would need positioning as a new HTTPAPI building block or as a section of a broader operation-resource draft. |

## Design Consequences

1. Lead with convergence: the corpus already shows broad use of a cancel
   affordance, especially `POST /.../{id}/cancel`.
2. Do not pitch a new route shape. Pitch interoperable semantics for an
   existing route shape and adjacent monitor-resource forms.
3. Treat the async-operation overlap as a design constraint, not only a strength.
   A cancellation draft must define enough operation-resource vocabulary for
   cancelability, terminal states, and status observation.
4. State the corpus denominator carefully. Prevalence claims are conditioned on
   a workflow/job/task-biased discovery corpus, not all HTTP APIs.
5. Put manual TP/FP validation before further score-model refinement. If the
   cancellation true-positive rate is weak, the RFC argument weakens at the
   root.
