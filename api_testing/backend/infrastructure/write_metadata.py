"""SQLite-backed metadata repository for backend write-flow orchestration."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.backend.domain.redaction import REDACTED_VALUE, is_sensitive_key
from api_testing.backend.domain.write_models import (
    ACTIVE_EXECUTION_STATUSES,
    Execution,
    ExecutionEvent,
    ExecutionMode,
    ExecutionStatus,
    JsonMap,
    RunConfig,
    RunConfigCreate,
    SpecCreate,
    UploadedSpec,
)


SCHEMA_VERSION = 1


class SQLiteWriteMetadataRepository:
    """Stores write-flow metadata in a local SQLite database."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create_spec(
        self,
        spec: SpecCreate,
        *,
        spec_id: str | None = None,
    ) -> UploadedSpec:
        resolved_id = spec_id or _new_id()
        created_at = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO specs (
                    spec_id, filename, title, content_hash, storage_path,
                    operation_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolved_id,
                    spec.filename,
                    spec.title,
                    spec.content_hash,
                    str(spec.storage_path),
                    spec.operation_count,
                    _to_text(created_at),
                ),
            )
        return self.get_spec(resolved_id)

    def list_specs(self) -> list[UploadedSpec]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM specs ORDER BY created_at, spec_id"
            ).fetchall()
        return [_spec_from_row(row) for row in rows]

    def get_spec(self, spec_id: str) -> UploadedSpec:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM specs WHERE spec_id = ?",
                (spec_id,),
            ).fetchone()
        if row is None:
            raise ArtifactNotFound(f"Spec not found: {spec_id}")
        return _spec_from_row(row)

    def create_run_config(
        self,
        config: RunConfigCreate,
        *,
        run_config_id: str | None = None,
    ) -> RunConfig:
        resolved_id = run_config_id or _new_id()
        created_at = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO run_configs (
                    run_config_id, name, spec_id, base_url, live_api,
                    request_budget, timeout_seconds, config_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolved_id,
                    config.name,
                    config.spec_id,
                    config.base_url,
                    int(config.live_api),
                    config.request_budget,
                    config.timeout_seconds,
                    json.dumps(config.config, sort_keys=True),
                    _to_text(created_at),
                ),
            )
        return self.get_run_config(resolved_id)

    def list_run_configs(self) -> list[RunConfig]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM run_configs ORDER BY created_at, run_config_id"
            ).fetchall()
        return [_run_config_from_row(row) for row in rows]

    def get_run_config(self, run_config_id: str) -> RunConfig:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM run_configs WHERE run_config_id = ?",
                (run_config_id,),
            ).fetchone()
        if row is None:
            raise ArtifactNotFound(f"Run config not found: {run_config_id}")
        return _run_config_from_row(row)

    def create_execution(
        self,
        *,
        spec_id: str,
        run_config_id: str,
        mode: ExecutionMode,
        run_name: str,
        execution_id: str | None = None,
    ) -> Execution:
        resolved_id = execution_id or _new_id()
        created_at = _now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO executions (
                    execution_id, spec_id, run_config_id, mode, status,
                    run_name, summary_json, created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    resolved_id,
                    spec_id,
                    run_config_id,
                    mode.value,
                    ExecutionStatus.QUEUED.value,
                    run_name,
                    "{}",
                    _to_text(created_at),
                ),
            )
        return self.get_execution(resolved_id)

    def create_execution_with_capacity(
        self,
        *,
        spec_id: str,
        run_config_id: str,
        mode: ExecutionMode,
        run_name: str,
        max_active_executions: int,
        execution_id: str | None = None,
    ) -> Execution:
        resolved_id = execution_id or _new_id()
        created_at = _now()
        active_values = tuple(status.value for status in ACTIVE_EXECUTION_STATUSES)
        placeholders = ",".join("?" for _ in active_values)
        with self._connect(immediate=True) as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM executions WHERE status IN ({placeholders})",
                active_values,
            ).fetchone()
            if int(row["count"]) >= max_active_executions:
                raise InvalidArtifactRequest("active execution limit reached")
            connection.execute(
                """
                INSERT INTO executions (
                    execution_id, spec_id, run_config_id, mode, status,
                    run_name, summary_json, created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                """,
                (
                    resolved_id,
                    spec_id,
                    run_config_id,
                    mode.value,
                    ExecutionStatus.QUEUED.value,
                    run_name,
                    "{}",
                    _to_text(created_at),
                ),
            )
            _insert_execution_event(
                connection,
                execution_id=resolved_id,
                event_type="queued",
                phase="execution",
                message="Execution queued",
                status=ExecutionStatus.QUEUED,
                metadata={},
                created_at=created_at,
            )
        return self.get_execution(resolved_id)

    def list_executions(self) -> list[Execution]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM executions ORDER BY created_at, execution_id"
            ).fetchall()
        return [_execution_from_row(row) for row in rows]

    def get_execution(self, execution_id: str) -> Execution:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        if row is None:
            raise ArtifactNotFound(f"Execution not found: {execution_id}")
        return _execution_from_row(row)

    def mark_execution_running(self, execution_id: str) -> Execution:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE executions
                SET status = ?, started_at = COALESCE(started_at, ?)
                WHERE execution_id = ?
                """,
                (ExecutionStatus.RUNNING.value, _to_text(now), execution_id),
            )
        return self.get_execution(execution_id)

    def request_execution_cancel(self, execution_id: str) -> Execution:
        execution = self.get_execution(execution_id)
        if execution.status not in ACTIVE_EXECUTION_STATUSES:
            return execution
        with self._connect() as connection:
            connection.execute(
                "UPDATE executions SET status = ? WHERE execution_id = ?",
                (ExecutionStatus.CANCEL_REQUESTED.value, execution_id),
            )
        return self.get_execution(execution_id)

    def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        *,
        summary: JsonMap | None = None,
        error_message: str | None = None,
    ) -> Execution:
        current = self.get_execution(execution_id)
        next_summary = dict(current.summary)
        if summary:
            next_summary.update(summary)
        if error_message:
            next_summary["error"] = error_message
        now = _now()
        completed_at = _to_text(now) if status in {
            ExecutionStatus.CANCELLED,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
        } else None
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE executions
                SET status = ?,
                    summary_json = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE execution_id = ?
                """,
                (
                    status.value,
                    json.dumps(next_summary, sort_keys=True),
                    completed_at,
                    execution_id,
                ),
            )
        return self.get_execution(execution_id)

    def finalize_active_execution(
        self,
        execution_id: str,
        status: ExecutionStatus,
        *,
        summary: JsonMap | None = None,
        error_message: str | None = None,
    ) -> Execution:
        now = _now()
        active_values = tuple(status_value.value for status_value in ACTIVE_EXECUTION_STATUSES)
        placeholders = ",".join("?" for _ in active_values)
        with self._connect(immediate=True) as connection:
            row = connection.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            if row is None:
                raise ArtifactNotFound(f"Execution not found: {execution_id}")
            current = _execution_from_row(row)
            if current.status not in ACTIVE_EXECUTION_STATUSES:
                return current
            next_summary = dict(current.summary)
            if summary:
                next_summary.update(summary)
            if error_message:
                next_summary["error"] = error_message
            completed_at = _to_text(now) if status in {
                ExecutionStatus.CANCELLED,
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
            } else None
            connection.execute(
                f"""
                UPDATE executions
                SET status = ?,
                    summary_json = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE execution_id = ? AND status IN ({placeholders})
                """,
                (
                    status.value,
                    json.dumps(next_summary, sort_keys=True),
                    completed_at,
                    execution_id,
                    *active_values,
                ),
            )
        return self.get_execution(execution_id)

    def finalize_active_execution_with_event(
        self,
        execution_id: str,
        status: ExecutionStatus,
        *,
        event_type: str,
        phase: str | None = None,
        message: str | None = None,
        summary: JsonMap | None = None,
        error_message: str | None = None,
    ) -> Execution:
        now = _now()
        active_values = tuple(status_value.value for status_value in ACTIVE_EXECUTION_STATUSES)
        placeholders = ",".join("?" for _ in active_values)
        with self._connect(immediate=True) as connection:
            row = connection.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            if row is None:
                raise ArtifactNotFound(f"Execution not found: {execution_id}")
            current = _execution_from_row(row)
            if current.status not in ACTIVE_EXECUTION_STATUSES:
                return current
            next_summary = dict(current.summary)
            if summary:
                next_summary.update(summary)
            if error_message:
                next_summary["error"] = error_message
            completed_at = _to_text(now) if status in {
                ExecutionStatus.CANCELLED,
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
            } else None
            connection.execute(
                f"""
                UPDATE executions
                SET status = ?,
                    summary_json = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE execution_id = ? AND status IN ({placeholders})
                """,
                (
                    status.value,
                    json.dumps(next_summary, sort_keys=True),
                    completed_at,
                    execution_id,
                    *active_values,
                ),
            )
            _insert_execution_event(
                connection,
                execution_id=execution_id,
                event_type=event_type,
                phase=phase,
                message=message,
                status=status,
                metadata=sanitize_metadata(summary or {}),
                created_at=now,
            )
        return self.get_execution(execution_id)

    def count_active_executions(self) -> int:
        active_values = tuple(status.value for status in ACTIVE_EXECUTION_STATUSES)
        placeholders = ",".join("?" for _ in active_values)
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM executions WHERE status IN ({placeholders})",
                active_values,
            ).fetchone()
        return int(row["count"])

    def is_cancel_requested(self, execution_id: str) -> bool:
        return self.get_execution(execution_id).status == ExecutionStatus.CANCEL_REQUESTED

    def append_execution_event(
        self,
        execution_id: str,
        *,
        event_type: str,
        phase: str | None = None,
        message: str | None = None,
        status: ExecutionStatus | None = None,
        metadata: JsonMap | None = None,
    ) -> ExecutionEvent:
        created_at = _now()
        sanitized_metadata = sanitize_metadata(metadata or {})
        with self._connect(immediate=True) as connection:
            event_id, sequence = _insert_execution_event(
                connection,
                execution_id=execution_id,
                event_type=event_type,
                phase=phase,
                message=message,
                status=status,
                metadata=sanitized_metadata,
                created_at=created_at,
            )
            row = connection.execute(
                "SELECT * FROM execution_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return _event_from_row(row)

    def list_execution_events(
        self,
        execution_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[ExecutionEvent]:
        self.get_execution(execution_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM execution_events
                WHERE execution_id = ? AND sequence > ?
                ORDER BY sequence
                """,
                (execution_id, after_sequence),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def reconcile_orphaned_executions(
        self,
        *,
        reason: str,
    ) -> list[Execution]:
        active_values = tuple(status.value for status in ACTIVE_EXECUTION_STATUSES)
        placeholders = ",".join("?" for _ in active_values)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM executions WHERE status IN ({placeholders}) ORDER BY created_at, execution_id",
                active_values,
            ).fetchall()
        reconciled: list[Execution] = []
        for row in rows:
            execution = _execution_from_row(row)
            updated = self.finalize_active_execution(
                execution.execution_id,
                ExecutionStatus.FAILED,
                summary={"reason": reason},
            )
            self.append_execution_event(
                execution.execution_id,
                event_type=reason,
                phase="execution",
                message="Execution marked failed during backend startup reconciliation",
                status=ExecutionStatus.FAILED,
                metadata={"reason": reason},
            )
            reconciled.append(updated)
        return reconciled

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS specs (
                    spec_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    operation_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_configs (
                    run_config_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    spec_id TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    live_api INTEGER NOT NULL,
                    request_budget INTEGER,
                    timeout_seconds INTEGER,
                    config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    spec_id TEXT NOT NULL,
                    run_config_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    run_name TEXT,
                    summary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS execution_events (
                    event_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    phase TEXT,
                    message TEXT,
                    status TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(execution_id, sequence)
                );

                CREATE INDEX IF NOT EXISTS idx_run_configs_spec_id
                    ON run_configs(spec_id);
                CREATE INDEX IF NOT EXISTS idx_executions_status_created_at
                    ON executions(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_execution_events_execution_sequence
                    ON execution_events(execution_id, sequence);
                """
            )
            count = connection.execute(
                "SELECT COUNT(*) AS count FROM schema_version"
            ).fetchone()["count"]
            if int(count) == 0:
                connection.execute(
                    "INSERT INTO schema_version(version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )

    @contextmanager
    def _connect(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 30000")
            if immediate:
                connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                sanitized[str(key)] = REDACTED_VALUE
            else:
                sanitized[str(key)] = sanitize_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    return value


def _insert_execution_event(
    connection: sqlite3.Connection,
    *,
    execution_id: str,
    event_type: str,
    phase: str | None,
    message: str | None,
    status: ExecutionStatus | None,
    metadata: JsonMap,
    created_at: datetime,
) -> tuple[str, int]:
    event_id = _new_id()
    row = connection.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 AS sequence "
        "FROM execution_events WHERE execution_id = ?",
        (execution_id,),
    ).fetchone()
    sequence = int(row["sequence"])
    connection.execute(
        """
        INSERT INTO execution_events (
            event_id, execution_id, sequence, event_type, phase,
            message, status, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            execution_id,
            sequence,
            event_type,
            phase,
            message,
            status.value if status else None,
            json.dumps(metadata, sort_keys=True),
            _to_text(created_at),
        ),
    )
    return event_id, sequence


def _spec_from_row(row: sqlite3.Row) -> UploadedSpec:
    return UploadedSpec(
        spec_id=str(row["spec_id"]),
        filename=str(row["filename"]),
        title=str(row["title"]),
        content_hash=str(row["content_hash"]),
        storage_path=Path(str(row["storage_path"])),
        operation_count=int(row["operation_count"]),
        created_at=_from_text(row["created_at"]),
    )


def _run_config_from_row(row: sqlite3.Row) -> RunConfig:
    return RunConfig(
        run_config_id=str(row["run_config_id"]),
        name=str(row["name"]),
        spec_id=str(row["spec_id"]),
        base_url=str(row["base_url"]),
        live_api=bool(row["live_api"]),
        request_budget=row["request_budget"],
        timeout_seconds=row["timeout_seconds"],
        config=json.loads(row["config_json"]),
        created_at=_from_text(row["created_at"]),
    )


def _execution_from_row(row: sqlite3.Row) -> Execution:
    return Execution(
        execution_id=str(row["execution_id"]),
        spec_id=str(row["spec_id"]),
        run_config_id=str(row["run_config_id"]),
        mode=ExecutionMode(str(row["mode"])),
        status=ExecutionStatus(str(row["status"])),
        run_name=row["run_name"],
        summary=json.loads(row["summary_json"]),
        created_at=_from_text(row["created_at"]),
        started_at=_from_text(row["started_at"]) if row["started_at"] else None,
        completed_at=_from_text(row["completed_at"]) if row["completed_at"] else None,
    )


def _event_from_row(row: sqlite3.Row) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=str(row["event_id"]),
        execution_id=str(row["execution_id"]),
        sequence=int(row["sequence"]),
        event_type=str(row["event_type"]),
        phase=row["phase"],
        message=row["message"],
        status=ExecutionStatus(str(row["status"])) if row["status"] else None,
        metadata=json.loads(row["metadata_json"]),
        created_at=_from_text(row["created_at"]),
    )


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_text(value: datetime) -> str:
    return value.isoformat()


def _from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)
