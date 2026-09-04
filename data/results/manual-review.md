# Manual Validation Review

Use this file to sample extractor quality before expanding the corpus.

Legend:

- TP: true positive
- FP: false positive
- FN candidate: likely missed route or concept
- Unclassified: evidence exists but pattern rules need refinement

## Evidence Samples

- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /task/{tasktype}` `rest/src/main/java/com/netflix/conductor/rest/controllers/AdminResource.java:50` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `Netflix/conductor` `POST /workflow` `rest/src/main/java/com/netflix/conductor/rest/controllers/MetadataResource.java:48` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `Netflix/conductor` `POST /workflow/validate` `rest/src/main/java/com/netflix/conductor/rest/controllers/MetadataResource.java:54` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /workflow/{name}` `rest/src/main/java/com/netflix/conductor/rest/controllers/MetadataResource.java:67` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /workflow` `rest/src/main/java/com/netflix/conductor/rest/controllers/MetadataResource.java:75` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /workflow/names-and-versions` `rest/src/main/java/com/netflix/conductor/rest/controllers/MetadataResource.java:81` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /workflow/latest-versions` `rest/src/main/java/com/netflix/conductor/rest/controllers/MetadataResource.java:87` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `Netflix/conductor` `POST /update/{workflowId}/task/{taskId}/{status}` `rest/src/main/java/com/netflix/conductor/rest/controllers/QueueAdminResource.java:65` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `Netflix/conductor` `POST /{name}` `rest/src/main/java/com/netflix/conductor/rest/controllers/WorkflowResource.java:66` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /search-by-tasks` `rest/src/main/java/com/netflix/conductor/rest/controllers/WorkflowResource.java:245` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `Netflix/conductor` `GET /search-by-tasks-v2` `rest/src/main/java/com/netflix/conductor/rest/controllers/WorkflowResource.java:260` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /jobs/` `src/integrations/prefect-dbt/prefect_dbt/cloud/_executor.py:239` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /jobs/` `src/integrations/prefect-dbt/prefect_dbt/cloud/_executor.py:332` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /task_runs/` `src/prefect/client/orchestration/__init__.py:887` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /task_run_states/` `src/prefect/client/orchestration/__init__.py:1022` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /task_runs/` `src/prefect/client/orchestration/__init__.py:1626` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /task_run_states/` `src/prefect/client/orchestration/__init__.py:1741` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `mutation-202-accepted` `PrefectHQ/prefect` `DELETE /owned-by/{resource_id:str}` `src/prefect/server/api/automations.py:239` confidence=0.84
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /name/{flow_name}/{deployment_name}` `src/prefect/server/api/deployments.py:475` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /get_scheduled_flow_runs` `src/prefect/server/api/deployments.py:617` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /bulk_delete` `src/prefect/server/api/deployments.py:716` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/resume_deployment` `src/prefect/server/api/deployments.py:804` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/pause_deployment` `src/prefect/server/api/deployments.py:823` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/create_flow_run` `src/prefect/server/api/deployments.py:855` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/create_flow_run/bulk` `src/prefect/server/api/deployments.py:996` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/schedules` `src/prefect/server/api/deployments.py:1259` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /lateness` `src/prefect/server/api/flow_runs.py:264` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/resume` `src/prefect/server/api/flow_runs.py:432` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /bulk_delete` `src/prefect/server/api/flow_runs.py:672` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/set_state` `src/prefect/server/api/task_runs.py:309` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /next-runs` `src/prefect/server/api/ui/flows.py:142` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{id:uuid}/get_runs` `src/prefect/server/api/work_queues.py:159` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /{name}/get_scheduled_flow_runs` `src/prefect/server/api/workers.py:809` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /deployments/{id}` `ui-v2/src/api/deployments/index.ts:197` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /deployments/` `ui-v2/src/api/deployments/index.ts:238` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /deployments/{id}/schedules` `ui-v2/src/api/deployments/index.ts:370` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /flow_runs/{id}` `ui-v2/src/api/flow-runs/index.ts:207` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /flow_runs/{id}/input/{key}` `ui-v2/src/api/flow-runs/index.ts:237` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /flow_runs/lateness` `ui-v2/src/api/flow-runs/index.ts:306` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /deployments/{id}/create_flow_run` `ui-v2/src/api/flow-runs/index.ts:426` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /flow_runs/{id}/set_state` `ui-v2/src/api/flow-runs/index.ts:472` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /flow_runs/{id}/resume` `ui-v2/src/api/flow-runs/index.ts:562` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /ui/flows/next-runs` `ui-v2/src/api/flows/index.ts:244` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /ui/task_runs/{id}` `ui-v2/src/api/task-runs/index.ts:215` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /ui/task_runs/{id}` `ui-v2/src/api/task-runs/index.ts:243` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `PrefectHQ/prefect` `POST /task_runs/{id}/set_state` `ui-v2/src/api/task-runs/index.ts:276` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /deployments/{id}` `ui-v2/src/components/dashboard/work-pools-card/work-pools-card.tsx:674` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /flow_runs/{id}/logs/download` `ui-v2/src/components/flow-runs/flow-run-details-page/flow-run-logs-download-button.tsx:26` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /flow_runs/{id}/graph-v2` `ui-v2/src/components/flow-runs/flow-run-graph/api.ts:21` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /deployments/{id}` `ui-v2/src/components/flows/detail/cells.tsx:13` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `PrefectHQ/prefect` `GET /deployments/{id}` `ui-v2/src/components/flows/detail/cells.tsx:26` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `RocketChat/Rocket.Chat` `POST /v1/commands.run` `apps/meteor/client/lib/chats/flows/processSlashCommand.ts:98` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `RocketChat/Rocket.Chat` `GET /v1/backfill/:roomId` `ee/packages/federation-matrix/src/api/_matrix/transactions.ts:467` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-202-accepted` `apache/airflow` `POST /enqueue-test` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/connections.py:383` confidence=0.84
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_run_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:132` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_run_id}/upstreamAssetEvents` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:270` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /{dag_run_id}/clear` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:309` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_run_id}/wait` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/dag_run.py:845` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_id}/logs/{try_number}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/log.py:79` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_id}/externalLogUrl/{try_number}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/log.py:188` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /clearTaskInstances` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/task_instances.py:850` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/public/tasks.py:95` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /next_run_assets/{dag_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/assets.py:143` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_run_id}/stats` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/dag_runs.py:36` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_id}/latest_run` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/dags.py:322` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /run_state_counts` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/dags.py:360` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /dagRuns/{dag_run_id}/deadlines` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/deadlines.py:56` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_id}/{run_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/gantt.py:36` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /runs/{dag_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/grid.py:267` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /partitioned_dag_runs` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/partitioned_dag_runs.py:243` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /pending_partitioned_dag_run/{dag_id}` `airflow-core/src/airflow/api_fastapi/core_api/routes/ui/partitioned_dag_runs.py:356` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_id}/{run_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/dag_runs.py:67` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /{dag_id}/{run_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/dag_runs.py:85` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /{dag_id}/{run_id}/clear` `airflow-core/src/airflow/api_fastapi/execution_api/routes/dag_runs.py:176` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{dag_id}/{run_id}/state` `airflow-core/src/airflow/api_fastapi/execution_api/routes/dag_runs.py:222` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /{task_instance_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/hitl.py:47` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_instance_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/hitl.py:137` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_instance_id}/previous-successful-dagrun` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:1090` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /previous/{dag_id}/{task_id}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:1195` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_instance_id}/validate-inlets-and-outlets` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_instances.py:1358` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /{task_instance_id}/start_date` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_reschedules.py:42` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /{task_instance_id}/{key:path}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/task_state_store.py:61` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /{dag_id}/{run_id}/{task_id}/{key:path}/item/{offset}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/xcoms.py:136` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /{dag_id}/{run_id}/{task_id}/{key:path}/slice` `airflow-core/src/airflow/api_fastapi/execution_api/routes/xcoms.py:181` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /{dag_id}/{run_id}/{task_id}/{key:path}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/xcoms.py:305` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /{dag_id}/{run_id}/{task_id}/{key:path}` `airflow-core/src/airflow/api_fastapi/execution_api/routes/xcoms.py:361` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-status-resource` `apache/airflow` `GET /logfile_path/{dag_id}/{task_id}/{run_id}/{try_number}/{map_index}` `providers/edge3/src/airflow/providers/edge3/worker_api/routes/logs.py:57` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `apache/airflow` `POST /push/{dag_id}/{task_id}/{run_id}/{try_number}/{map_index}` `providers/edge3/src/airflow/providers/edge3/worker_api/routes/logs.py:81` confidence=0.7
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `apache/airflow` `GET /jobs` `providers/edge3/src/airflow/providers/edge3/worker_api/routes/ui.py:102` confidence=0.6
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `argoproj/argo-cd` `POST /api/v1/applications/{name}/resource/actions` `assets/swagger.json:1465` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `argoproj/argo-cd` `POST /api/v1/applications/{name}/resource/actions/v2` `assets/swagger.json:1604` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/archived-workflows` `api/openapi-spec/swagger.json:20` confidence=0.68
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/archived-workflows-label-keys` `api/openapi-spec/swagger.json:122` confidence=0.68
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/archived-workflows-label-values` `api/openapi-spec/swagger.json:151` confidence=0.68
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/archived-workflows/{uid}` `api/openapi-spec/swagger.json:242` confidence=0.68
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/cluster-workflow-templates` `api/openapi-spec/swagger.json:396` confidence=0.68
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `argoproj/argo-workflows` `POST /api/v1/cluster-workflow-templates` `api/openapi-spec/swagger.json:396` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `post-job-resource` `argoproj/argo-workflows` `POST /api/v1/cluster-workflow-templates/lint` `api/openapi-spec/swagger.json:512` confidence=0.78
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/cluster-workflow-templates/{name}` `api/openapi-spec/swagger.json:544` confidence=0.68
- [ ] TP  [ ] FP  [ ] Unclassified — `http-async-operation` `get-operation-resource` `argoproj/argo-workflows` `GET /api/v1/cron-workflows/{namespace}` `api/openapi-spec/swagger.json:692` confidence=0.68

## False Negative Candidates

- [ ] Add routes or files that manual inspection shows were missed.

## Repository Errors

- No repository errors recorded.
