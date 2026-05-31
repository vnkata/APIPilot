import {
  getGetExecutionApiV1ExecutionsExecutionIdGetQueryKey,
  getListExecutionEventsApiV1ExecutionsExecutionIdEventsGetQueryKey,
  getListExecutionsApiV1ExecutionsGetQueryKey,
  useCancelExecutionApiV1ExecutionsExecutionIdCancelPost,
  useCreateExecutionApiV1ExecutionsPost,
  useGetExecutionApiV1ExecutionsExecutionIdGet,
  useGetExecutionRunApiV1ExecutionsExecutionIdRunGet,
  useListExecutionEventsApiV1ExecutionsExecutionIdEventsGet,
  useListExecutionsApiV1ExecutionsGet,
} from '../../shared/api/generated/executions/executions'
import {
  getGetRunApiV1RunsRunNameGetQueryKey,
  getListRunsApiV1RunsGetQueryKey,
} from '../../shared/api/generated/runs/runs'
import {
  getListRunConfigsApiV1RunConfigsGetQueryKey,
  useCreateRunConfigApiV1RunConfigsPost,
  useGetRunConfigApiV1RunConfigsRunConfigIdGet,
  useListRunConfigsApiV1RunConfigsGet,
  useValidateRunConfigApiV1RunConfigsValidatePost,
} from '../../shared/api/generated/run-configs/run-configs'
import {
  getGetSpecApiV1SpecsSpecIdGetQueryKey,
  getPreviewSpecOperationsApiV1SpecsSpecIdOperationsGetQueryKey,
  getListSpecsApiV1SpecsGetQueryKey,
  useCreateSpecApiV1SpecsPost,
  useGetSpecApiV1SpecsSpecIdGet,
  useListSpecsApiV1SpecsGet,
  usePreviewSpecOperationsApiV1SpecsSpecIdOperationsGet,
} from '../../shared/api/generated/specs/specs'

export const builderQueryKeys = {
  executions: getListExecutionsApiV1ExecutionsGetQueryKey,
  execution: getGetExecutionApiV1ExecutionsExecutionIdGetQueryKey,
  executionEvents: getListExecutionEventsApiV1ExecutionsExecutionIdEventsGetQueryKey,
  run: getGetRunApiV1RunsRunNameGetQueryKey,
  runConfigs: getListRunConfigsApiV1RunConfigsGetQueryKey,
  runs: getListRunsApiV1RunsGetQueryKey,
  spec: getGetSpecApiV1SpecsSpecIdGetQueryKey,
  specOperations: getPreviewSpecOperationsApiV1SpecsSpecIdOperationsGetQueryKey,
  specs: getListSpecsApiV1SpecsGetQueryKey,
}

export const useSpecs = useListSpecsApiV1SpecsGet
export const useCreateSpec = useCreateSpecApiV1SpecsPost
export const useSpec = useGetSpecApiV1SpecsSpecIdGet
export const useSpecOperations = usePreviewSpecOperationsApiV1SpecsSpecIdOperationsGet

export const useRunConfigs = useListRunConfigsApiV1RunConfigsGet
export const useRunConfig = useGetRunConfigApiV1RunConfigsRunConfigIdGet
export const useValidateRunConfig = useValidateRunConfigApiV1RunConfigsValidatePost
export const useCreateRunConfig = useCreateRunConfigApiV1RunConfigsPost

export const useExecutions = useListExecutionsApiV1ExecutionsGet
export const useCreateExecution = useCreateExecutionApiV1ExecutionsPost
export const useExecution = useGetExecutionApiV1ExecutionsExecutionIdGet
export const useCancelExecution = useCancelExecutionApiV1ExecutionsExecutionIdCancelPost
export const useExecutionEvents = useListExecutionEventsApiV1ExecutionsExecutionIdEventsGet
export const useExecutionRun = useGetExecutionRunApiV1ExecutionsExecutionIdRunGet
