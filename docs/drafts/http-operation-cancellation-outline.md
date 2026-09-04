# HTTP Operation Cancellation Draft Outline

Working title: **Cancellation Semantics for HTTP Operation Resources**

This outline is cancellation-first. It does not try to standardize every
long-running operation pattern. It defines semantics for a cancel affordance
that already appears across independent implementations.

## 1. Abstract

Define an HTTP API profile for requesting cancellation of an operation, learning
whether cancellation was accepted, and observing the resulting terminal state.
The profile applies to long-running or asynchronous operations that expose an
operation resource, status monitor, or equivalent observable operation handle.

## 2. Introduction

- Many HTTP APIs start work that cannot finish within the original request.
- Existing practice commonly exposes a cancellation affordance.
- The mined corpus shows strong shape convergence around
  `POST /.../{operation-id}/cancel`, with adjacent `PUT`, `PATCH`, `GET`, and
  `DELETE` variants.
- The gap is not endpoint naming. The gap is shared semantics:
  cancelability advertisement, accepted-but-not-complete responses,
  too-late-to-cancel responses, final-state observation, and retry behavior.

## 3. Scope

In scope:

- cancellation request semantics;
- server indication that an operation is cancelable;
- server indication that a cancellation request was accepted for processing;
- server indication that cancellation is impossible or too late;
- status-resource observation of cancellation progress and terminal result;
- retry and idempotency considerations for cancellation requests.

Out of scope:

- defining a complete generic operation-resource model;
- requiring a single URI shape for all APIs;
- transport mechanisms other than HTTP;
- domain-specific rollback or compensation guarantees.

## 4. Relationship to Operation Resources

The document can be positioned in one of two ways:

1. standalone cancellation profile over an abstract operation handle;
2. a cancellation section inside a broader operation-resource draft.

The standalone profile should define only the minimal operation vocabulary it
needs:

- operation identifier or monitor URI;
- nonterminal states;
- terminal states including successful cancellation and failed cancellation;
- optional result or error representation;
- expiry of observable operation state.

This directly addresses the likely review question: cancellation is tightly
coupled to operation resources, but the corpus shows enough convergence around
the cancellation affordance to justify specifying that slice first.

## 5. Advertising Cancelability

Candidate mechanisms to discuss:

- link relation from operation/status representation to cancel target;
- boolean or state-field indication in the operation representation;
- documented operation contract when representation links are absent.

The draft should prefer discoverable affordances over naming conventions alone.

## 6. Cancellation Request

The draft should treat `POST /.../{id}/cancel` as the dominant deployed shape,
not as the only conformant shape.

Candidate normative model:

- a cancellation request asks the server to stop or prevent further processing
  of an identified operation;
- cancellation is generally best-effort unless the API contract makes stronger
  guarantees;
- the server MUST NOT report successful cancellation before the operation has
  reached a terminal canceled state, unless it clearly distinguishes request
  acceptance from completion;
- duplicate cancellation requests SHOULD be safe and produce the same observable
  operation state.

## 7. Response Semantics

Candidate status-code mapping:

| Situation | Candidate status | Notes |
| --- | --- | --- |
| cancellation request accepted, operation not terminal | `202 Accepted` | Include or link to the operation/status resource and polling guidance. |
| operation already canceled | `200 OK` or `204 No Content` | Response should be idempotent and not imply a new cancellation attempt. |
| operation completed and can no longer be canceled | `409 Conflict` or `422 Unprocessable Content` | Use Problem Details for machine-readable reason. |
| operation does not support cancellation | `405 Method Not Allowed` or `409 Conflict` | `405` fits unsupported method on a known resource; `409` fits state/contract conflict. |
| operation handle not found or expired | `404 Not Found` or `410 Gone` | Expiry semantics should be explicit. |
| cancellation itself is represented as a separate operation | `202 Accepted` | Link to the cancellation-status resource and distinguish it from the original operation. |

The draft should be careful not to overload `204 No Content`: it can mean “the
request completed”, but not necessarily “the original operation is now canceled”
unless the API contract says so.

## 8. Observing Terminal State

Clients need a stable way to learn whether the original operation:

- was canceled;
- completed despite the cancellation request;
- failed while cancellation was pending;
- never supported cancellation;
- expired before the client observed the terminal state.

The draft should define recommended terminal state names or a small vocabulary,
while allowing application-specific representation fields.

## 9. Retry and Idempotency

Cancellation requests are frequently retried after network loss. The draft
should specify:

- safe handling of duplicate cancellation requests;
- interaction with `Idempotency-Key` or service-specific repeatability headers;
- how clients distinguish a lost cancellation response from a non-received
  cancellation request;
- whether a later retry can change the terminal result.

## 10. Error Representation

Use Problem Details for structured cancellation errors where the response is not
an operation representation. Candidate problem types:

- operation-not-cancelable;
- cancellation-too-late;
- cancellation-conflict;
- operation-expired.

## 11. Security and Privacy Considerations

- Cancellation is a state-changing authority and requires authorization.
- Guessable operation IDs can become denial-of-service handles.
- Cancel links may need expiration and audience scoping.
- Status resources can leak existence, progress, ownership, and failure details.
- Replay protection may be needed for signed cancel URLs.

## 12. IANA Considerations

Possible registries or registrations:

- optional link relation for cancellation affordances;
- optional Problem Details types for common cancellation failures;
- no new method registration.

## 13. Evidence Appendix

The appendix should cite:

- the 5,000-repository refined corpus;
- strict cancellation family count;
- shape-convergence table with pattern-family memberships clearly labeled;
- TP/FP sample results before any WG adoption request.
