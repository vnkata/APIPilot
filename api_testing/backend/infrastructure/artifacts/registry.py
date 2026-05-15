"""Known APIPilot cache artifact registry."""

from __future__ import annotations

from dataclasses import dataclass

from api_testing.backend.domain.models import ArtifactKind, MediaType, RawPolicy


@dataclass(frozen=True, slots=True)
class ArtifactDefinition:
    artifact_id: str
    relative_path: str
    kind: ArtifactKind
    media_type: MediaType
    raw_policy: RawPolicy
    raw_supported: bool = True
    summary_supported: bool = True


KNOWN_ARTIFACTS: tuple[ArtifactDefinition, ...] = (
    ArtifactDefinition(
        "baseline_specification",
        "baseline_specification.json",
        ArtifactKind.SPECIFICATION,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "specification",
        "specification.json",
        ArtifactKind.SPECIFICATION,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "configuration",
        "configuration.json",
        ArtifactKind.CONFIGURATION,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "contextual_memory",
        "contextual_memory.json",
        ArtifactKind.MEMORY,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "dependency_sequences",
        "dependency_sequences.json",
        ArtifactKind.GRAPH,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "reports",
        "reports.json",
        ArtifactKind.REPORTS,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "semantic_property_dependency_graph",
        "semantic_property_dependency_graph.json",
        ArtifactKind.GRAPH,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "heuristic_edges",
        "heuristic_edges.json",
        ArtifactKind.GRAPH,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "gpt_edges",
        "gpt_edges.json",
        ArtifactKind.GRAPH,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "constraint_miner",
        "constraint_miner.json",
        ArtifactKind.COMBINED_CONSTRAINTS,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "static_constraint_miner",
        "static_constraint_miner.json",
        ArtifactKind.STATIC_CONSTRAINTS,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "static_constraint_miner_request_response",
        "static_constraint_miner_request_response.json",
        ArtifactKind.STATIC_CONSTRAINTS,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "static_constraint_miner_response_properties",
        "static_constraint_miner_response_properties.json",
        ArtifactKind.STATIC_CONSTRAINTS,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "dynamic_constraint_miner",
        "dynamic_constraint_miner.json",
        ArtifactKind.DYNAMIC_CONSTRAINTS,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
    ArtifactDefinition(
        "test_cases_json",
        "test_cases.json",
        ArtifactKind.TEST_CASES,
        MediaType.APPLICATION_JSON,
        RawPolicy.SANITIZED_TEST_CASES,
    ),
    ArtifactDefinition(
        "invariants_csv",
        "invariants.csv",
        ArtifactKind.INVARIANTS,
        MediaType.TEXT_CSV,
        RawPolicy.RAW_CSV,
    ),
    ArtifactDefinition(
        "gpt_usages",
        "gpt-4.1-mini_usages.json",
        ArtifactKind.USAGE,
        MediaType.APPLICATION_JSON,
        RawPolicy.RAW_JSON,
    ),
)

KNOWN_ARTIFACTS_BY_ID = {
    artifact.artifact_id: artifact for artifact in KNOWN_ARTIFACTS
}


def har_artifact_definition(session_id: str) -> ArtifactDefinition:
    return ArtifactDefinition(
        artifact_id=f"history_{session_id}",
        relative_path=f"history/{session_id}.har",
        kind=ArtifactKind.HAR_SESSION,
        media_type=MediaType.APPLICATION_JSON,
        raw_policy=RawPolicy.SANITIZED_HAR_SESSION,
    )
