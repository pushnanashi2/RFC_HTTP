# Candidate: http-async-operation

## Summary

- Score: 75
- Independent families: 17
- Raw repositories: 17
- Observed patterns: 5
- Best seeded standards coverage: partial

## Observed Practice

- `get-operation-resource`: 15 families, 15 repositories
  - `apache/airflow` `GET /partitioned_dag_runs` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/partitioned_dag_runs.py:243` confidence=0.6
  - `apache/airflow` `GET /pending_partitioned_dag_run/{dag_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/partitioned_dag_runs.py:356` confidence=0.6
  - `apache/airflow` `GET /next_run_assets/{dag_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/assets.py:143` confidence=0.6
- `get-status-resource`: 5 families, 5 repositories
  - `apache/airflow` `GET /{task_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/tasks.py:95` confidence=0.78
  - `apache/airflow` `GET /{dag_run_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:132` confidence=0.78
  - `apache/airflow` `GET /{dag_run_id}/upstreamAssetEvents` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:270` confidence=0.78
- `mutation-202-accepted`: 4 families, 4 repositories
  - `PrefectHQ/prefect` `DELETE /owned-by/{resource_id:str}` `src/prefect/server/api/automations.py:239` confidence=0.84
  - `go-gitea/gitea` `DELETE /orgs/{org}/repos` `templates/swagger/v1-swagger.generated.json:4429` confidence=0.92
  - `go-gitea/gitea` `DELETE /orgs/{org}/repos` `templates/swagger/v1-openapi3.generated.json:15664` confidence=0.92
- `post-202-accepted`: 8 families, 8 repositories
  - `apache/airflow` `POST /enqueue-test` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/connections.py:383` confidence=0.84
  - `windmill-labs/windmill` `POST /settings/object_storage_usage` `backend/windmill-api/openapi.yaml:1804` confidence=0.92
  - `windmill-labs/windmill` `POST /settings/run_log_cleanup` `backend/windmill-api/openapi.yaml:1818` confidence=0.92
- `post-job-resource`: 14 families, 14 repositories
  - `apache/airflow` `POST /{dag_run_id}/clear` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:309` confidence=0.7
  - `apache/airflow` `POST /clearTaskInstances` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/task_instances.py:850` confidence=0.7
  - `apache/airflow` `POST /{dag_id}/{run_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/dag_runs.py:85` confidence=0.7

## Standards Gap

- `RFC9110` partial: Defines 202 Accepted, Location, methods, and resource semantics, but not a reusable long-running operation lifecycle pattern.
- `RFC8288` adjacent: Can express links to status or result resources, but does not define operation lifecycle relations.
- `RFC7240` adjacent: Defines request preferences such as respond-async, but not a complete operation resource shape.
- `RFC9457` adjacent: Covers error representation, not operation lifecycle or polling interactions.
- `draft-ietf-httpapi-idempotency-key-header` adjacent: Helps retry non-idempotent creation requests, but does not define async operation lifecycle, status, or cancellation patterns.

## Why High

- Observed across multiple independent implementation families.
- Multiple interaction patterns indicate real implementation divergence.
- Asynchronous operations shape polling, progress, result, and retry behavior.

## Why Low

- Seeded standards already cover part of the concept.

## Counterarguments

- Stage-1 extraction may undercount dynamic framework routes.
- OpenAPI-documented APIs may not represent internal server practice.
- An implementation guide or profile may be more appropriate than a new RFC.

## Candidate Specification Scope

- Define only reusable HTTP interaction semantics observed across independent implementations.
- Avoid standardizing implementation bugs or framework-specific conventions.
