import type {
  ArtifactCatalogResponse,
  ArtifactContentResponse,
} from '../../shared/api/generated/model'

type ArtifactMetadata = ArtifactCatalogResponse['artifacts'][number]

export type MetadataFieldDiff = {
  field: keyof ArtifactMetadata
  left: unknown
  right: unknown
}

export type ArtifactMetadataDiff = {
  changed: MetadataFieldDiff[]
  status: 'changed' | 'left-only' | 'match' | 'right-only'
}

export type JsonDiffItem = {
  kind: 'added' | 'changed' | 'removed'
  left?: unknown
  path: string
  right?: unknown
}

export type JsonDiffResult = {
  items: JsonDiffItem[]
  summary: {
    added: number
    changed: number
    removed: number
  }
}

const metadataFields: Array<keyof ArtifactMetadata> = [
  'artifact_id',
  'kind',
  'media_type',
  'raw_policy',
  'raw_supported',
  'relative_path',
  'size_bytes',
  'summary_supported',
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isEqual(left: unknown, right: unknown) {
  return JSON.stringify(left) === JSON.stringify(right)
}

function joinPath(basePath: string, key: string) {
  if (!basePath) return key
  return key.startsWith('[') ? `${basePath}${key}` : `${basePath}.${key}`
}

function walkJsonDiff(left: unknown, right: unknown, path: string, items: JsonDiffItem[]) {
  if (isEqual(left, right)) return

  if (Array.isArray(left) || Array.isArray(right)) {
    const leftArray = Array.isArray(left) ? left : []
    const rightArray = Array.isArray(right) ? right : []
    const length = Math.max(leftArray.length, rightArray.length)

    for (let index = 0; index < length; index += 1) {
      const nextPath = joinPath(path, `[${index}]`)
      if (index >= leftArray.length) {
        items.push({ kind: 'added', path: nextPath, right: rightArray[index] })
      } else if (index >= rightArray.length) {
        items.push({ kind: 'removed', left: leftArray[index], path: nextPath })
      } else {
        walkJsonDiff(leftArray[index], rightArray[index], nextPath, items)
      }
    }
    return
  }

  if (isRecord(left) || isRecord(right)) {
    const leftRecord = isRecord(left) ? left : {}
    const rightRecord = isRecord(right) ? right : {}
    const keys = Array.from(new Set([...Object.keys(leftRecord), ...Object.keys(rightRecord)])).sort()

    keys.forEach((key) => {
      const nextPath = joinPath(path, key)
      if (!(key in leftRecord)) {
        items.push({ kind: 'added', path: nextPath, right: rightRecord[key] })
      } else if (!(key in rightRecord)) {
        items.push({ kind: 'removed', left: leftRecord[key], path: nextPath })
      } else {
        walkJsonDiff(leftRecord[key], rightRecord[key], nextPath, items)
      }
    })
    return
  }

  items.push({ kind: 'changed', left, path: path || '$', right })
}

export function buildArtifactMetadataDiff(
  left?: ArtifactMetadata,
  right?: ArtifactMetadata,
): ArtifactMetadataDiff {
  if (left && !right) return { changed: [], status: 'left-only' }
  if (!left && right) return { changed: [], status: 'right-only' }
  if (!left || !right) return { changed: [], status: 'match' }

  const changed = metadataFields
    .filter((field) => !isEqual(left[field], right[field]))
    .map((field) => ({ field, left: left[field], right: right[field] }))

  return {
    changed,
    status: changed.length > 0 ? 'changed' : 'match',
  }
}

export function buildJsonDiff(left: unknown, right: unknown): JsonDiffResult {
  const items: JsonDiffItem[] = []
  walkJsonDiff(left, right, '', items)
  return {
    items,
    summary: {
      added: items.filter((item) => item.kind === 'added').length,
      changed: items.filter((item) => item.kind === 'changed').length,
      removed: items.filter((item) => item.kind === 'removed').length,
    },
  }
}

export function extractComparableContent(content?: ArtifactContentResponse) {
  if (!content) return undefined
  if ('value' in content.content) return content.content.value
  if ('text' in content.content) return content.content.text
  if ('rows' in content.content) return content.content.rows
  return content.content
}
