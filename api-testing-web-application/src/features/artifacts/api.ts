import {
  useGetArtifactContentApiV1RunsRunNameArtifactsArtifactIdContentGet,
  useListArtifactsApiV1RunsRunNameArtifactsGet,
} from '../../shared/api/generated/artifacts/artifacts'

export const useArtifacts = useListArtifactsApiV1RunsRunNameArtifactsGet
export const useArtifactContent = useGetArtifactContentApiV1RunsRunNameArtifactsArtifactIdContentGet
