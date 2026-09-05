# HTTP Cancellation Pilot Log

Status: not run.

This file records pilot rows for the independent A/B LLM labeling workflow. The
pilot is a prompt-validation exercise and must not be mixed into final estimates
if prompts, models, temperature, or adjudication rules change after the pilot.

## Planned Design

- Size: 30 to 50 route rows.
- Allocation: roughly half from `delete-operation-resource` rows and half from
  `post-subresource-cancel` rows.
- Exclusion: avoid census-only strata.
- Labeling temperature: 0.

## Stop/Revise Rules

- Disagreement rate above 40%: revise prompts or criteria before full labeling.
- Disagreement rate below 5%: widen prompt or model differences before full
  labeling.
- `ambiguous` rate above 50%: revise label criteria before full labeling.

## Pilot Evidence IDs

No pilot rows have been selected yet.
