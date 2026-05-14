import type { GraphEdgeResponse } from '../../shared/api/generated/model'

export function getGraphEdgeId(edge: GraphEdgeResponse) {
  const evidence = edge.similar_parameters
    .map((item) => [item.value1, item.value2, item.in_value].filter(Boolean).join('|'))
    .sort()
    .join(';')

  return `${edge.from_node}=>${edge.to_node}::${evidence}`
}
