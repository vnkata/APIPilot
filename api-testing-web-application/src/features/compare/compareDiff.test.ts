import { artifactCatalog, artifactContent } from '../../test/fixtures'
import { buildArtifactMetadataDiff, buildJsonDiff, extractComparableContent } from './compareDiff'

describe('compareDiff', () => {
  it('builds artifact metadata differences without requiring backend support', () => {
    const diff = buildArtifactMetadataDiff(
      artifactCatalog.artifacts[0],
      {
        ...artifactCatalog.artifacts[0],
        media_type: 'text/plain',
        raw_policy: 'raw_text',
        size_bytes: 4096,
      },
    )

    expect(diff.changed).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ field: 'media_type', left: 'application/json', right: 'text/plain' }),
        expect.objectContaining({ field: 'raw_policy', left: 'raw_json', right: 'raw_text' }),
        expect.objectContaining({ field: 'size_bytes', left: 2048, right: 4096 }),
      ]),
    )
    expect(diff.status).toBe('changed')
  })

  it('builds structural JSON path diffs for added, removed, and changed values', () => {
    const diff = buildJsonDiff(
      { operations: { get: { method: 'get', status: 200 }, removed: true } },
      { operations: { get: { method: 'post', status: 200 }, added: true } },
    )

    expect(diff.summary).toMatchObject({ added: 1, changed: 1, removed: 1 })
    expect(diff.items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kind: 'changed', path: 'operations.get.method' }),
        expect.objectContaining({ kind: 'added', path: 'operations.added' }),
        expect.objectContaining({ kind: 'removed', path: 'operations.removed' }),
      ]),
    )
  })

  it('extracts comparable content from artifact content responses', () => {
    expect(extractComparableContent(artifactContent)).toMatchObject({
      operations: {
        'get-/items': { method: 'get', path: '/items' },
      },
    })
  })
})
