import { defineConfig } from 'orval';

export default defineConfig({
  fastapi: {
    input: {
      target: './openapi.json',
    },
    output: {
      mode: 'tags-split',
      target: './src/shared/api/generated/api.ts',
      schemas: './src/shared/api/generated/model',
      client: 'react-query',
      httpClient: 'axios',
      override: {
        mutator: {
          path: './src/shared/api/httpClient.ts',
          name: 'customInstance',
        },
        query: {
          options: {
            staleTime: 30_000,
            retry: 1,
          },
        },
      },
    },
  },
});
