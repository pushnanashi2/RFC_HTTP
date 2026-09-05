# HTTP Cancellation Pilot Log

Status: Labeler A complete; Labeler B not run.

This file records pilot rows for the independent A/B LLM labeling workflow. The
pilot is a prompt-validation exercise and must not be mixed into final estimates
if prompts, models, temperature, or adjudication rules change after the pilot.

## Step 0 Context Columns

- `operationSummary` is present in the blinded labeling view.
- `operationDescription` is present in the blinded labeling view.
- Current snapshot has non-empty `operationSummary` values for 135 of 635
  labeling rows and 7 of 40 pilot rows.
- Current snapshot has no retained OpenAPI operation descriptions, so
  `operationDescription` is empty for this pilot. The extractor now preserves
  descriptions for future collection runs.

## Pilot Sample

- Seed: `2026090501`
- Rows: 40
- Allocation: 20 `delete-operation-resource` rows and 20
  `post-subresource-cancel` rows.
- Output: `docs/validation/http-cancellation-pilot-2026-09-05.csv`

## Labeler A

- Status: complete
- Output: `docs/validation/http-cancellation-pilot-labels-a.csv`
- Model: `codex-current-session; dated snapshot ID unavailable in environment`
- Prompt hash: `cd0c951c7128ad4ca00f7ce7ebff23ef5bf8adfc03ed5e5f1aa5b32a2e1324a3`
- Prompt version: `b95fe0defe18081cb30dca5e278b659e9ae5207e`
- Labeling date: `2026-09-05`
- Temperature: `0`

Label distribution for operation-vs-domain rows:

| Label | Count |
| --- | ---: |
| `ambiguous` | 7 |
| `domain-state-transition` | 0 |
| `operation-cancellation` | 13 |

DELETE audit label distribution:

| Label | Count |
| --- | ---: |
| `ambiguous` | 3 |
| `cancellation` | 0 |
| `deletion-or-archival` | 17 |

## Stop/Revise Rules

- Disagreement rate above 40%: revise prompts or criteria before full labeling.
- Disagreement rate below 5%: widen prompt or model differences before full
  labeling.
- `ambiguous` rate above 50%: revise label criteria before full labeling.

## Pilot Sample IDs

- `cancel-0199-route-003`
- `cancel-0207-route-002`
- `cancel-0215-route-001`
- `cancel-0216-route-004`
- `cancel-0216-route-010`
- `cancel-0222-route-001`
- `cancel-0239-route-001`
- `cancel-0242-route-003`
- `cancel-0248-route-001`
- `cancel-0255-route-001`
- `cancel-0261-route-003`
- `cancel-0268-route-002`
- `cancel-0271-route-002`
- `cancel-0281-route-002`
- `cancel-0288-route-003`
- `cancel-0293-route-003`
- `cancel-0305-route-002`
- `cancel-0307-route-002`
- `cancel-0312-route-001`
- `cancel-0319-route-001`
- `cancel-0002-route-001`
- `cancel-0003-route-005`
- `cancel-0003-route-006`
- `cancel-0004-route-002`
- `cancel-0005-route-002`
- `cancel-0005-route-004`
- `cancel-0005-route-006`
- `cancel-0008-route-002`
- `cancel-0010-route-003`
- `cancel-0014-route-001`
- `cancel-0023-route-001`
- `cancel-0037-route-004`
- `cancel-0038-route-001`
- `cancel-0039-route-002`
- `cancel-0041-route-003`
- `cancel-0044-route-005`
- `cancel-0045-route-004`
- `cancel-0047-route-001`
- `cancel-0062-route-001`
- `cancel-0074-route-004`
