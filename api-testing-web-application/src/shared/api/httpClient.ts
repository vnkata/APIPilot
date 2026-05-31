import Axios, { type AxiosError, type AxiosRequestConfig } from 'axios';

import { runtimeConfig } from '../config/runtimeConfig';

export const AXIOS_INSTANCE = Axios.create({
  baseURL: runtimeConfig.apiBaseUrl,
  timeout: runtimeConfig.apiTimeoutMs,
  headers: {
    Accept: 'application/json',
  },
});

/**
 * Orval custom mutator.
 *
 * Orval will call this function from generated TanStack Query hooks.
 */
export const customInstance = <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  return AXIOS_INSTANCE({
    ...config,
    ...options,
  }).then(({ data }) => data);
};

export type ErrorType<Error> = AxiosError<Error>;
export type BodyType<BodyData> = BodyData;
