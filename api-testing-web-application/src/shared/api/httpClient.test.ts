import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import axios from 'axios'

import { AXIOS_INSTANCE, customInstance } from './httpClient'

describe('httpClient', () => {
  it('does not attach localStorage access_token in the no-auth local tool', async () => {
    window.localStorage.setItem('access_token', 'should-not-be-sent')
    const originalAdapter = AXIOS_INSTANCE.defaults.adapter
    let capturedConfig: InternalAxiosRequestConfig | undefined

    const adapter: AxiosAdapter = async (config) => {
      capturedConfig = config
      return {
        config,
        data: { status: 'ok' },
        headers: new axios.AxiosHeaders(),
        status: 200,
        statusText: 'OK',
      } satisfies AxiosResponse
    }

    AXIOS_INSTANCE.defaults.adapter = adapter

    try {
      await customInstance({ method: 'GET', url: '/health' })
    } finally {
      AXIOS_INSTANCE.defaults.adapter = originalAdapter
      window.localStorage.clear()
    }

    expect(capturedConfig?.headers.Authorization).toBeUndefined()
  })
})
