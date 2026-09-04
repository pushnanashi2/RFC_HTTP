# Candidate: http-cancellation

## Summary

- Score: 74
- Independent families: 15
- Raw repositories: 15
- Observed patterns: 5
- Best seeded standards coverage: adjacent

## Observed Practice

- `delete-operation-resource`: 10 families, 10 repositories
  - `apache/airflow` `DELETE /{dag_run_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:155` confidence=0.56
  - `apache/airflow` `DELETE /{task_instance_id}/{key:path}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_state_store.py:93` confidence=0.56
  - `apache/airflow` `DELETE /{task_instance_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_state_store.py:104` confidence=0.56
- `get-cancel-link`: 1 families, 1 repositories
  - `windmill-labs/windmill` `GET /w/{workspace}/jobs_u/cancel/{id}/{resume_id}/{signature}` `backend/windmill-api/openapi.yaml:16657` confidence=0.82
  - `windmill-labs/windmill` `GET /w/{workspace}/jobs_u/cancel/{id}/{resume_id}/{signature}` `backend/windmill-api/openapi-deref.json:22130` confidence=0.82
  - `windmill-labs/windmill` `GET /w/{workspace}/jobs_u/cancel/{id}/{resume_id}/{signature}` `backend/windmill-api/openapi-deref.yaml:22969` confidence=0.82
- `post-action-cancel`: 3 families, 3 repositories
  - `windmill-labs/windmill` `POST /w/{workspace}/jobs/queue/cancel_selection` `backend/windmill-api/openapi.yaml:14750` confidence=0.96
  - `windmill-labs/windmill` `POST /w/{workspace}/trigger/{trigger_kind}/cancel_suspended_trigger_jobs/{trigger_path}` `backend/windmill-api/openapi.yaml:14848` confidence=0.96
  - `windmill-labs/windmill` `POST /w/{workspace}/jobs_u/queue/cancel/{id}` `backend/windmill-api/openapi.yaml:16045` confidence=0.96
- `post-subresource-cancel`: 9 families, 9 repositories
  - `n8n-io/n8n` `POST /executions/stop` `packages/cli/src/public-api/v1/openapi.decorator-routes.generated.yml:20` confidence=0.96
  - `n8n-io/n8n` `POST /executions/{executionId}/stop` `packages/cli/src/public-api/v1/openapi.decorator-routes.generated.yml:23` confidence=0.96
  - `n8n-io/n8n` `POST /rest/executions/${executionId}/stop` `packages/testing/playwright/services/workflow-api-helper.ts:411` confidence=0.88
- `put-action-cancel`: 1 families, 1 repositories
  - `argoproj/argo-workflows` `PUT /api/v1/workflows/{namespace}/{name}/stop` `api/openapi-spec/swagger.json:3790` confidence=0.82
  - `argoproj/argo-workflows` `PUT /api/v1/workflows/{namespace}/{name}/terminate` `api/openapi-spec/swagger.json:3878` confidence=0.82

## Standards Gap

- `RFC9110` adjacent: Defines method semantics such as DELETE and PATCH, but not cancellation-specific lifecycle guarantees.
- `RFC9457` adjacent: Can represent cancellation errors, but does not define cancellation interaction semantics.

## Why High

- Observed across multiple independent implementation families.
- Multiple interaction patterns indicate real implementation divergence.
- Existing seeded standards do not fully cover the observed concept.
- Cancellation affects client interoperability and safe operation lifecycle handling.

## Why Low


## Counterarguments

- Stage-1 extraction may undercount dynamic framework routes.
- OpenAPI-documented APIs may not represent internal server practice.
- Cancellation semantics may depend on domain-specific safety guarantees.

## Candidate Specification Scope

- Define only reusable HTTP interaction semantics observed across independent implementations.
- Avoid standardizing implementation bugs or framework-specific conventions.
