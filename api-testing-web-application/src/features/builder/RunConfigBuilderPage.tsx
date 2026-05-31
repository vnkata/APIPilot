import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import SaveIcon from '@mui/icons-material/Save'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import type { ExecutionResponse, RunConfigRequest } from '../../shared/api/generated/model'
import { normalizeApiError } from '../../shared/api/errors'
import { PageHeader } from '../../shared/ui/PageHeader'
import { Panel } from '../../shared/ui/Panel'
import { QueryState } from '../../shared/ui/QueryState'
import {
  builderQueryKeys,
  useCreateExecution,
  useCreateRunConfig,
  useSpec,
  useSpecs,
  useValidateRunConfig,
} from './api'
import { builderPath, encodePathPart, isSensitiveHeaderName } from './builderUtils'
import { loadRunConfigDraft, saveRunConfigDraft } from './runConfigDrafts'

type HeaderDraft = {
  name: string
  refName: string
  type: 'env' | 'plain'
  value: string
}

type RunConfigBuilderPageProps = {
  search: {
    specId?: string
  }
}

const steps = ['Spec', 'Basic', 'AI', 'Headers', 'Validate']

function numberOrUndefined(value: number | '') {
  return value === '' ? undefined : value
}

function headerPayload(headers: HeaderDraft[]): RunConfigRequest['headers'] {
  return Object.fromEntries(
    headers
      .filter((header) => header.name.trim())
      .map((header) => [
        header.name.trim(),
        header.type === 'env'
          ? { type: 'env' as const, name: header.refName.trim() || `${header.name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_')}_REF` }
          : header.value,
      ]),
  )
}

export function RunConfigBuilderPage({ search }: RunConfigBuilderPageProps) {
  const draft = useMemo(() => loadRunConfigDraft(), [])
  const [activeStep, setActiveStep] = useState(0)
  const [specId, setSpecId] = useState(search.specId ?? draft?.specId ?? '')
  const [configName, setConfigName] = useState(draft?.configName ?? 'APIPilot dry run')
  const [baseUrl, setBaseUrl] = useState('')
  const [liveApi, setLiveApi] = useState(draft?.liveApi ?? false)
  const [requestBudget, setRequestBudget] = useState<number | ''>(draft?.requestBudget ?? 5)
  const [timeoutSeconds, setTimeoutSeconds] = useState<number | ''>(draft?.timeoutSeconds ?? 10)
  const [numGenerations, setNumGenerations] = useState<number | ''>(draft?.numGenerations ?? 1)
  const [numTestCases, setNumTestCases] = useState<number | ''>(draft?.numTestCases ?? 20)
  const [mutationRatio, setMutationRatio] = useState<number | ''>(draft?.mutationRatio ?? 0)
  const [headerMutationRatio, setHeaderMutationRatio] = useState<number | ''>(draft?.headerMutationRatio ?? 0.5)
  const [asyncMode, setAsyncMode] = useState(draft?.asyncMode ?? false)
  const [constraintMining, setConstraintMining] = useState(draft?.constraintMining ?? false)
  const [llmProvider, setLlmProvider] = useState(draft?.llmProvider ?? '')
  const [llmModel, setLlmModel] = useState(draft?.llmModel ?? '')
  const [llmApiKeyRef, setLlmApiKeyRef] = useState('')
  const [embeddingProvider, setEmbeddingProvider] = useState(draft?.embeddingProvider ?? '')
  const [embeddingModel, setEmbeddingModel] = useState(draft?.embeddingModel ?? '')
  const [headers, setHeaders] = useState<HeaderDraft[]>([{ name: '', refName: '', type: 'env', value: '' }])
  const [successMessage, setSuccessMessage] = useState('')
  const [createdExecution, setCreatedExecution] = useState<ExecutionResponse>()
  const [liveConfirmOpen, setLiveConfirmOpen] = useState(false)
  const specsQuery = useSpecs()
  const specQuery = useSpec(specId, { query: { enabled: Boolean(specId) } })
  const queryClient = useQueryClient()
  const validateMutation = useValidateRunConfig()
  const createRunConfig = useCreateRunConfig({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: builderQueryKeys.runConfigs() })
        setSuccessMessage('Config created')
      },
    },
  })
  const createExecution = useCreateExecution({
    mutation: {
      onSuccess: async (execution) => {
        await queryClient.invalidateQueries({ queryKey: builderQueryKeys.executions() })
        if (execution.run_name) {
          await queryClient.invalidateQueries({ queryKey: builderQueryKeys.runs() })
        }
        setCreatedExecution(execution)
        setSuccessMessage(`Execution ${execution.execution_id} created`)
      },
    },
  })

  useEffect(() => {
    saveRunConfigDraft({
      asyncMode,
      baseUrl,
      configName,
      constraintMining,
      embeddingModel,
      embeddingProvider,
      headerDrafts: headers,
      headerMutationRatio: numberOrUndefined(headerMutationRatio),
      liveApi,
      llmModel,
      llmProvider,
      mutationRatio: numberOrUndefined(mutationRatio),
      numGenerations: numberOrUndefined(numGenerations),
      numTestCases: numberOrUndefined(numTestCases),
      requestBudget: numberOrUndefined(requestBudget),
      specId,
      timeoutSeconds: numberOrUndefined(timeoutSeconds),
    })
  }, [
    asyncMode,
    baseUrl,
    configName,
    constraintMining,
    embeddingModel,
    embeddingProvider,
    headerMutationRatio,
    headers,
    liveApi,
    llmModel,
    llmProvider,
    mutationRatio,
    numGenerations,
    numTestCases,
    requestBudget,
    specId,
    timeoutSeconds,
  ])

  const payload: RunConfigRequest = {
    async_mode: asyncMode,
    base_url: baseUrl,
    constraint_mining: constraintMining,
    embedding: embeddingProvider && embeddingModel ? { provider: embeddingProvider, model: embeddingModel } : undefined,
    header_mutation_ratio: Number(numberOrUndefined(headerMutationRatio) ?? 0.5),
    headers: headerPayload(headers),
    live_api: liveApi,
    llm: llmProvider && llmModel
      ? {
          api_key: llmApiKeyRef ? { type: 'env', name: llmApiKeyRef } : undefined,
          provider: llmProvider,
          model: llmModel,
        }
      : undefined,
    mutation_ratio: Number(numberOrUndefined(mutationRatio) ?? 0),
    name: configName,
    num_generations: Number(numberOrUndefined(numGenerations) ?? 1),
    num_test_cases: Number(numberOrUndefined(numTestCases) ?? 20),
    request_budget: numberOrUndefined(requestBudget),
    spec_id: specId,
    timeout_seconds: numberOrUndefined(timeoutSeconds),
  }

  const validation = validateMutation.data
  const validationError = validateMutation.error ? normalizeApiError(validateMutation.error) : undefined
  const createError = createRunConfig.error ? normalizeApiError(createRunConfig.error) : undefined
  const executionError = createExecution.error ? normalizeApiError(createExecution.error) : undefined
  const canSubmit = Boolean(specId && configName && baseUrl)
  const modeLabel = liveApi ? 'live' : 'dry run'
  const validationStatus = validateMutation.isPending
    ? 'checking'
    : validation
      ? validation.valid
        ? 'valid'
        : 'needs attention'
      : 'not run'

  function updateHeader(index: number, patch: Partial<HeaderDraft>) {
    setHeaders((current) => current.map((header, currentIndex) => {
      if (currentIndex !== index) return header
      const next = { ...header, ...patch }
      if (patch.name && isSensitiveHeaderName(patch.name)) next.type = 'env'
      return next
    }))
  }

  function validateConfig() {
    validateMutation.mutate({ data: payload })
  }

  function createConfig() {
    createRunConfig.mutate({ data: payload })
  }

  function createConfigAndRun() {
    if (liveApi) {
      setLiveConfirmOpen(true)
      return
    }
    createRunConfig.mutate(
      { data: payload },
      {
        onSuccess: (config) => {
          createExecution.mutate({ data: { mode: 'dry_run', run_config_id: config.run_config_id, spec_id: config.spec_id } })
        },
      },
    )
  }

  function createLiveExecutionAfterConfig() {
    setLiveConfirmOpen(false)
    createRunConfig.mutate(
      { data: payload },
      {
        onSuccess: (config) => {
          createExecution.mutate({ data: { mode: 'live', run_config_id: config.run_config_id, spec_id: config.spec_id } })
        },
      },
    )
  }

  return (
    <Stack spacing={2}>
      <PageHeader
        eyebrow="Builder"
        subtitle="Create validated APIPilot run configs from uploaded specs. Sensitive runtime values should be referenced by environment variable name."
        title="Run Config Builder"
      />

      <Panel
        aria-label="Run config summary"
        role="region"
        subtitle="Desktop guidance for the next execution before you commit the config."
        title="Config summary"
      >
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 3 }}>
            <Typography color="text.secondary" variant="caption">
              Mode
            </Typography>
            <Typography sx={{ fontWeight: 800 }} variant="body2">
              Mode: {modeLabel}
            </Typography>
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <Typography color="text.secondary" variant="caption">
              Validation
            </Typography>
            <Typography sx={{ fontWeight: 800 }} variant="body2">
              Validation: {validationStatus}
            </Typography>
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <Typography color="text.secondary" variant="caption">
              Budget
            </Typography>
            <Typography sx={{ fontWeight: 800 }} variant="body2">
              {requestBudget || 'No'} requests · {timeoutSeconds || 'No'}s timeout
            </Typography>
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <Typography color="text.secondary" variant="caption">
              Spec
            </Typography>
            <Typography sx={{ fontWeight: 800, overflowWrap: 'anywhere' }} variant="body2">
              {specQuery.data?.title ?? specId ?? 'Choose a spec'}
            </Typography>
          </Grid>
        </Grid>
        <Alert severity={liveApi ? 'warning' : 'info'} sx={{ mt: 2 }} variant="outlined">
          Dry run uses deterministic local execution. Live mode can send requests to the configured target and requires explicit confirmation.
        </Alert>
      </Panel>

      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <QueryState
        empty={(specsQuery.data?.specs ?? []).length === 0}
        emptyAction={
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
            <Button component="a" href={builderPath('/specs')} variant="contained">
              Upload spec
            </Button>
            <Button component="a" href={builderPath('/specs')} variant="outlined">
              Go to Spec Manager
            </Button>
          </Stack>
        }
        emptyDescription="Upload a spec before creating a run config."
        emptyTitle="No uploaded specs"
        error={specsQuery.error}
        isError={specsQuery.isError}
        isLoading={specsQuery.isLoading}
      >
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Spec"
                onChange={(event) => setSpecId(event.target.value)}
                select
                value={specId}
              >
                {(specsQuery.data?.specs ?? []).map((spec) => (
                  <MenuItem key={spec.spec_id} value={spec.spec_id}>
                    {spec.title} · {spec.operation_count} operations
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Config name"
                onChange={(event) => setConfigName(event.target.value)}
                value={configName}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Base URL"
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="https://example.test"
                value={baseUrl}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                label="Request budget"
                onChange={(event) => setRequestBudget(Number(event.target.value) || '')}
                type="number"
                value={requestBudget}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                label="Timeout seconds"
                onChange={(event) => setTimeoutSeconds(Number(event.target.value) || '')}
                type="number"
                value={timeoutSeconds}
              />
            </Grid>
          </Grid>

          {specQuery.data ? (
            <Alert severity="info">
              Selected spec: {specQuery.data.title} with {specQuery.data.operation_count} operations.
            </Alert>
          ) : null}

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>AI configuration</AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField fullWidth label="LLM provider" onChange={(event) => setLlmProvider(event.target.value)} value={llmProvider} />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField fullWidth label="LLM model" onChange={(event) => setLlmModel(event.target.value)} value={llmModel} />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField fullWidth label="LLM API key env variable" onChange={(event) => setLlmApiKeyRef(event.target.value)} value={llmApiKeyRef} />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField fullWidth label="Embedding provider" onChange={(event) => setEmbeddingProvider(event.target.value)} value={embeddingProvider} />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField fullWidth label="Embedding model" onChange={(event) => setEmbeddingModel(event.target.value)} value={embeddingModel} />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>Headers</AccordionSummary>
            <AccordionDetails>
              <Stack spacing={2}>
                {headers.map((header, index) => (
                  <Grid container key={index} spacing={2}>
                    <Grid size={{ xs: 12, md: 3 }}>
                      <TextField
                        fullWidth
                        label="Header name"
                        onChange={(event) => updateHeader(index, { name: event.target.value })}
                        value={header.name}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, md: 2 }}>
                      <TextField
                        fullWidth
                        label="Header value type"
                        onChange={(event) => updateHeader(index, { type: event.target.value as HeaderDraft['type'] })}
                        select
                        value={header.type}
                      >
                        <MenuItem value="env">Env ref</MenuItem>
                        <MenuItem disabled={isSensitiveHeaderName(header.name)} value="plain">Plain</MenuItem>
                      </TextField>
                    </Grid>
                    <Grid size={{ xs: 12, md: 4 }}>
                      {header.type === 'env' ? (
                        <TextField
                          fullWidth
                          label="Env variable name"
                          onChange={(event) => updateHeader(index, { refName: event.target.value })}
                          value={header.refName}
                        />
                      ) : (
                        <TextField
                          fullWidth
                          label="Plain header value"
                          onChange={(event) => updateHeader(index, { value: event.target.value })}
                          value={header.value}
                        />
                      )}
                    </Grid>
                  </Grid>
                ))}
                <Box>
                  <Button onClick={() => setHeaders((current) => [...current, { name: '', refName: '', type: 'env', value: '' }])}>
                    Add header
                  </Button>
                </Box>
              </Stack>
            </AccordionDetails>
          </Accordion>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>Advanced</AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 3 }}>
                  <TextField fullWidth label="Generations" onChange={(event) => setNumGenerations(Number(event.target.value) || '')} type="number" value={numGenerations} />
                </Grid>
                <Grid size={{ xs: 12, md: 3 }}>
                  <TextField fullWidth label="Test cases" onChange={(event) => setNumTestCases(Number(event.target.value) || '')} type="number" value={numTestCases} />
                </Grid>
                <Grid size={{ xs: 12, md: 3 }}>
                  <TextField fullWidth label="Mutation ratio" onChange={(event) => setMutationRatio(Number(event.target.value))} type="number" value={mutationRatio} />
                </Grid>
                <Grid size={{ xs: 12, md: 3 }}>
                  <TextField fullWidth label="Header mutation ratio" onChange={(event) => setHeaderMutationRatio(Number(event.target.value))} type="number" value={headerMutationRatio} />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControlLabel control={<Checkbox checked={asyncMode} onChange={(event) => setAsyncMode(event.target.checked)} />} label="Async mode" />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControlLabel control={<Checkbox checked={constraintMining} onChange={(event) => setConstraintMining(event.target.checked)} />} label="Constraint mining" />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <FormControlLabel control={<Checkbox checked={liveApi} onChange={(event) => setLiveApi(event.target.checked)} />} label="Live API mode" />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>

          <Stack
            direction="row"
            spacing={1}
            sx={(theme) => ({
              bgcolor: theme.apiTesting.surface.overlay,
              border: '1px solid',
              borderColor: theme.apiTesting.border.default,
              borderRadius: 1.5,
              bottom: 16,
              flexWrap: 'wrap',
              p: 1,
              position: { md: 'sticky' },
              zIndex: 2,
            })}
          >
            <Button disabled={activeStep === 0} onClick={() => setActiveStep((step) => Math.max(0, step - 1))}>Back</Button>
            <Button disabled={activeStep === steps.length - 1} onClick={() => setActiveStep((step) => Math.min(steps.length - 1, step + 1))}>Next</Button>
            <Button disabled={!canSubmit || validateMutation.isPending} onClick={validateConfig} startIcon={<CheckCircleIcon />} variant="outlined">
              Validate config
            </Button>
            <Button disabled={!canSubmit || createRunConfig.isPending} onClick={createConfig} startIcon={<SaveIcon />} variant="contained">
              Create config
            </Button>
            <Button disabled={!canSubmit || createRunConfig.isPending || createExecution.isPending} onClick={createConfigAndRun} startIcon={<PlayArrowIcon />} variant="contained">
              Create and run
            </Button>
          </Stack>

          {validation ? (
            <Alert severity={validation.valid ? 'success' : 'warning'}>
              {validation.valid ? 'Configuration is valid' : validation.errors.join('; ')}
            </Alert>
          ) : null}
          {successMessage ? <Alert severity="success">{successMessage}</Alert> : null}
          {createdExecution ? (
            <Alert
              action={
                <Button
                  component="a"
                  href={builderPath(`/executions/${encodePathPart(createdExecution.execution_id)}`)}
                  size="small"
                  startIcon={<OpenInNewIcon />}
                >
                  Open execution detail
                </Button>
              }
              severity="success"
            >
              Execution created. Track events and open the generated run from the detail page.
            </Alert>
          ) : null}
          {validationError ? <Alert severity="error">{validationError.message}</Alert> : null}
          {createError ? <Alert severity="error">{createError.message}</Alert> : null}
          {executionError ? <Alert severity="error">{executionError.message}</Alert> : null}
        </Stack>
      </QueryState>

      <Dialog onClose={() => setLiveConfirmOpen(false)} open={liveConfirmOpen}>
        <DialogTitle>Confirm live API execution</DialogTitle>
        <DialogContent>
          <Typography>
            Live mode can send requests to the target API. Confirm the base URL, request budget, timeout, and backend allowlist before starting.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLiveConfirmOpen(false)}>Cancel</Button>
          <Button color="warning" onClick={createLiveExecutionAfterConfig} variant="contained">
            Start live execution
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
