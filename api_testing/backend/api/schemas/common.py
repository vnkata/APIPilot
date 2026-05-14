from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from api_testing.backend.domain.models import GroupCount, Pagination, SanitizedBody


class BackendBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(BackendBaseModel):
    code: str
    message: str


class ErrorResponse(BackendBaseModel):
    error: ErrorDetail


class HealthResponse(BackendBaseModel):
    status: str = "ok"


class PaginationMetadata(BackendBaseModel):
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)

    @classmethod
    def from_domain(cls, pagination: Pagination) -> "PaginationMetadata":
        return cls(
            limit=pagination.limit,
            offset=pagination.offset,
            total=pagination.total,
        )


class GroupCountResponse(BackendBaseModel):
    key: str | None = None
    count: int = Field(ge=0)

    @classmethod
    def from_domain(cls, group: GroupCount) -> "GroupCountResponse":
        return cls(key=group.key, count=group.count)


class SanitizedBodyResponse(BackendBaseModel):
    included: bool
    truncated: bool
    content: JsonValue | None = None
    preview: str | None = None
    size_bytes: int = Field(ge=0)
    redaction_count: int = Field(ge=0)

    @classmethod
    def from_domain(cls, body: SanitizedBody) -> "SanitizedBodyResponse":
        return cls(
            included=body.included,
            truncated=body.truncated,
            content=body.content,
            preview=body.preview,
            size_bytes=body.size_bytes,
            redaction_count=body.redaction_count,
        )
