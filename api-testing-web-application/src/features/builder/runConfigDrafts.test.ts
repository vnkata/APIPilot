import {
  loadRunConfigDraft,
  runConfigDraftsStorageKey,
  saveRunConfigDraft,
} from './runConfigDrafts'

describe('runConfigDrafts', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('persists only non-sensitive run config draft fields', () => {
    saveRunConfigDraft({
      asyncMode: true,
      baseUrl: 'https://private.example.test',
      configName: 'Items run',
      constraintMining: true,
      headerDrafts: [
        { name: 'Authorization', refName: 'API_TOKEN', type: 'env' },
        { name: 'X-Debug', type: 'plain', value: 'visible' },
      ],
      llmModel: 'gpt-4.1-mini',
      llmProvider: 'openai',
      numGenerations: 2,
      numTestCases: 10,
      requestBudget: 5,
      specId: 'spec-items',
      timeoutSeconds: 10,
    })

    const rawValue = window.localStorage.getItem(runConfigDraftsStorageKey) ?? ''
    expect(rawValue).toContain('Items run')
    expect(rawValue).toContain('spec-items')
    expect(rawValue).not.toContain('private.example')
    expect(rawValue).not.toContain('Authorization')
    expect(rawValue).not.toContain('API_TOKEN')
    expect(rawValue).not.toContain('visible')

    expect(loadRunConfigDraft()).toMatchObject({
      asyncMode: true,
      configName: 'Items run',
      constraintMining: true,
      llmModel: 'gpt-4.1-mini',
      llmProvider: 'openai',
      numGenerations: 2,
      numTestCases: 10,
      requestBudget: 5,
      specId: 'spec-items',
      timeoutSeconds: 10,
    })
  })

  it('fails safely when the stored draft is invalid', () => {
    window.localStorage.setItem(runConfigDraftsStorageKey, '{broken')

    expect(loadRunConfigDraft()).toBeUndefined()
  })
})
