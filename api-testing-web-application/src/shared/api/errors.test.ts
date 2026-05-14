import axios from 'axios'

import { normalizeApiError } from './errors'

describe('normalizeApiError', () => {
  it('uses backend error code and message for typed API errors', () => {
    const error = new axios.AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        config: {
          headers: new axios.AxiosHeaders(),
        },
        data: {
          error: {
            code: 'invalid_request',
            message: 'sort_by is not valid',
          },
        },
        headers: {},
        status: 400,
        statusText: 'Bad Request',
      },
    )

    expect(normalizeApiError(error)).toEqual({
      code: 'invalid_request',
      message: 'sort_by is not valid',
      status: 400,
      title: 'Invalid request',
    })
  })

  it('formats FastAPI validation errors without leaking raw payload details', () => {
    const error = new axios.AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        config: {
          headers: new axios.AxiosHeaders(),
        },
        data: {
          detail: [
            {
              loc: ['query', 'limit'],
              msg: 'Input should be greater than or equal to 1',
              type: 'greater_than_equal',
            },
          ],
        },
        headers: {},
        status: 422,
        statusText: 'Unprocessable Entity',
      },
    )

    expect(normalizeApiError(error)).toMatchObject({
      code: 'validation_error',
      message: 'query.limit: Input should be greater than or equal to 1',
      status: 422,
      title: 'Validation error',
    })
  })
})
