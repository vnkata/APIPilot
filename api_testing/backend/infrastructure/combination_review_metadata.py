from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid
from typing import Any, Iterator

from pydantic import JsonValue

from api_testing.backend.domain.models import CombinationDetail
from api_testing.backend.domain.review_models import (
    CombinationReview,
    CombinationReviewEvent,
    CounterExampleCase,
)
from api_testing.backend.application.review_services.counter_example_requests import (
    has_redacted_literal,
    merge_validation_errors,
    redacted_executable_validation_error,
)


class SQLiteCombinationReviewRepository:
    """SQLite metadata repository for Combination HITL review state."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def review_key_for_detail(run_name: str, detail: CombinationDetail) -> str:
        return review_key(
            run_name=run_name,
            operation_id=detail.operation_id,
            property_path=detail.property_path,
            static_constraint=detail.static_constraint,
            dynamic_constraint=detail.dynamic_constraint,
        )

    def list_reviews_for_run(self, run_name: str) -> dict[str, CombinationReview]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM combination_reviews WHERE run_name = ?",
                (run_name,),
            ).fetchall()
        return {str(row["review_key"]): _review_from_row(row) for row in rows}

    def get_or_create_review(
        self,
        *,
        run_name: str,
        combination_id: str,
        review_key: str,
    ) -> CombinationReview:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT * FROM combination_reviews WHERE review_key = ?",
                (review_key,),
            ).fetchone()
            if row is None:
                now = _now()
                conn.execute(
                    """
                    INSERT INTO combination_reviews (
                        review_key, run_name, combination_id, review_state,
                        decision_source, manual_decision, rationale,
                        custom_final_constraint, runtime_recommendation,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?)
                    """,
                    (review_key, run_name, combination_id, "PENDING_REVIEW", now, now),
                )
                _insert_event(
                    conn,
                    review_key=review_key,
                    event_type="review_created",
                    metadata={"combination_id": combination_id},
                )
            else:
                now = _now()
                conn.execute(
                    """
                    UPDATE combination_reviews
                    SET combination_id = ?, updated_at = ?
                    WHERE review_key = ?
                    """,
                    (combination_id, now, review_key),
                )
        return self.get_review(review_key)

    def get_review(self, review_key: str) -> CombinationReview:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM combination_reviews WHERE review_key = ?",
                (review_key,),
            ).fetchone()
        if row is None:
            raise KeyError(review_key)
        return _review_from_row(row)

    def list_cases(self, review_key: str) -> list[CounterExampleCase]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM counter_example_cases
                WHERE review_key = ?
                ORDER BY created_at, case_id
                """,
                (review_key,),
            ).fetchall()
        return [_case_from_row(row) for row in rows]

    def list_events(self, review_key: str) -> list[CombinationReviewEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM combination_review_events
                WHERE review_key = ?
                ORDER BY sequence
                """,
                (review_key,),
            ).fetchall()
        return [_event_from_row(row) for row in rows]

    def create_draft_cases(
        self,
        *,
        review_key: str,
        cases: list[dict[str, JsonValue]],
        source: str,
        generation_id: str,
        planner_version: str | None,
        source_metadata: JsonValue | None = None,
    ) -> list[CounterExampleCase]:
        with self._transaction() as conn:
            now = _now()
            for case in cases:
                case_source_metadata = {}
                if isinstance(case.get("source_metadata"), dict):
                    case_source_metadata.update(case["source_metadata"])
                if isinstance(source_metadata, dict):
                    case_source_metadata.update(source_metadata)
                conn.execute(
                    """
                    INSERT INTO counter_example_cases (
                        case_id, review_key, case_state, request,
                        request_private, request_display, source,
                        rationale, generation_id, target_truth_vector, risk,
                        expected_observation, validation_error, planner_version,
                        source_metadata, runtime_verdict, runtime_result,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                    """,
                    (
                        f"cec_{uuid.uuid4().hex}",
                        review_key,
                        "DRAFT",
                        _to_json(case.get("request_display") or case.get("request") or {}),
                        _to_json(case.get("request_private") or case.get("request") or {}),
                        _to_json(case.get("request_display") or case.get("request") or {}),
                        source,
                        case.get("rationale"),
                        generation_id,
                        _to_json(case.get("target_truth_vector")),
                        case.get("risk"),
                        case.get("expected_observation"),
                        _to_json(case.get("validation_error")),
                        planner_version,
                        _to_json(case_source_metadata),
                        now,
                        now,
                    ),
                )
            self._set_review_state_in_tx(conn, review_key, "DRAFT_READY")
            _insert_event(
                conn,
                review_key=review_key,
                event_type="drafts_generated",
                metadata={
                    "case_count": len(cases),
                    "source": source,
                    "generation_id": generation_id,
                },
            )
        return self.list_cases(review_key)

    def get_idempotency_record(
        self,
        *,
        review_key: str,
        action: str,
        idempotency_key: str,
    ) -> dict[str, JsonValue] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM combination_review_idempotency
                WHERE review_key = ? AND action = ? AND idempotency_key = ?
                """,
                (review_key, action, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        return {
            "review_key": str(row["review_key"]),
            "action": str(row["action"]),
            "idempotency_key": str(row["idempotency_key"]),
            "request_hash": str(row["request_hash"]),
            "result_metadata": json.loads(str(row["result_metadata"])),
        }

    def record_idempotency(
        self,
        *,
        review_key: str,
        action: str,
        idempotency_key: str,
        request_hash: str,
        result_metadata: JsonValue,
    ) -> None:
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO combination_review_idempotency (
                    review_key, action, idempotency_key, request_hash,
                    result_metadata, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    review_key,
                    action,
                    idempotency_key,
                    request_hash,
                    _to_json(result_metadata),
                    _now(),
                ),
            )

    def update_case(
        self,
        *,
        review_key: str,
        case_id: str,
        case_state: str,
        rationale: str | None,
        request_private: JsonValue | None = None,
        request_display: JsonValue | None = None,
        validation_error: JsonValue | None = None,
    ) -> CounterExampleCase:
        now = _now()
        with self._transaction() as conn:
            row = conn.execute(
                """
                SELECT * FROM counter_example_cases
                WHERE review_key = ? AND case_id = ?
                """,
                (review_key, case_id),
            ).fetchone()
            if row is None:
                raise KeyError(case_id)
            request_private_payload = (
                _to_json(request_private)
                if request_private is not None
                else row["request_private"] or row["request"]
            )
            request_display_payload = (
                _to_json(request_display)
                if request_display is not None
                else row["request_display"] or row["request"]
            )
            validation_error_payload = row["validation_error"]
            if validation_error is not None:
                validation_error_payload = _to_json(
                    merge_validation_errors(
                        _json_or_none(row["validation_error"]),
                        validation_error,
                    )
                )
            conn.execute(
                """
                UPDATE counter_example_cases
                SET case_state = ?, rationale = ?, request = ?,
                    request_private = ?, request_display = ?,
                    validation_error = ?, updated_at = ?
                WHERE review_key = ? AND case_id = ?
                """,
                (
                    case_state,
                    rationale,
                    request_display_payload,
                    request_private_payload,
                    request_display_payload,
                    validation_error_payload,
                    now,
                    review_key,
                    case_id,
                ),
            )
            if case_state == "APPROVED":
                self._set_review_state_in_tx(conn, review_key, "APPROVED")
            _insert_event(
                conn,
                review_key=review_key,
                event_type="case_updated",
                metadata={"case_id": case_id, "case_state": case_state},
            )
        cases = [case for case in self.list_cases(review_key) if case.case_id == case_id]
        if not cases:
            raise KeyError(case_id)
        return cases[0]

    def complete_case_run(
        self,
        *,
        review_key: str,
        case_id: str,
        runtime_verdict: str,
        runtime_result: JsonValue,
    ) -> None:
        now = _now()
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE counter_example_cases
                SET case_state = ?, runtime_verdict = ?, runtime_result = ?, updated_at = ?
                WHERE review_key = ? AND case_id = ?
                """,
                (
                    "EXECUTED",
                    runtime_verdict,
                    _to_json(runtime_result),
                    now,
                    review_key,
                    case_id,
                ),
            )
            _insert_event(
                conn,
                review_key=review_key,
                event_type="case_executed",
                metadata={"case_id": case_id, "runtime_verdict": runtime_verdict},
            )

    def set_runtime_recommendation(
        self,
        *,
        review_key: str,
        runtime_recommendation: str,
    ) -> CombinationReview:
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE combination_reviews
                SET review_state = ?, runtime_recommendation = ?, updated_at = ?
                WHERE review_key = ?
                """,
                ("RUN_COMPLETED", runtime_recommendation, _now(), review_key),
            )
            _insert_event(
                conn,
                review_key=review_key,
                event_type="run_completed",
                metadata={"runtime_recommendation": runtime_recommendation},
            )
        return self.get_review(review_key)

    def finalize_review(
        self,
        *,
        review_key: str,
        manual_decision: str,
        rationale: str,
        custom_final_constraint: str | None,
    ) -> CombinationReview:
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE combination_reviews
                SET review_state = ?, decision_source = ?, manual_decision = ?,
                    rationale = ?, custom_final_constraint = ?, updated_at = ?
                WHERE review_key = ?
                """,
                (
                    "FINAL_CONFIRMED",
                    "human",
                    manual_decision,
                    rationale,
                    custom_final_constraint,
                    _now(),
                    review_key,
                ),
            )
            _insert_event(
                conn,
                review_key=review_key,
                event_type="review_finalized",
                metadata={"manual_decision": manual_decision},
            )
        return self.get_review(review_key)

    def reopen_review(self, *, review_key: str, rationale: str) -> CombinationReview:
        with self._transaction() as conn:
            conn.execute(
                """
                UPDATE combination_reviews
                SET review_state = ?, decision_source = NULL, manual_decision = NULL,
                    rationale = ?, custom_final_constraint = NULL, updated_at = ?
                WHERE review_key = ?
                """,
                ("REOPENED", rationale, _now(), review_key),
            )
            _insert_event(
                conn,
                review_key=review_key,
                event_type="review_reopened",
                metadata={"rationale": rationale},
            )
        return self.get_review(review_key)

    def _set_review_state_in_tx(
        self,
        conn: sqlite3.Connection,
        review_key: str,
        review_state: str,
    ) -> None:
        conn.execute(
            """
            UPDATE combination_reviews
            SET review_state = ?, updated_at = ?
            WHERE review_key = ?
            """,
            (review_state, _now(), review_key),
        )

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _initialize(self) -> None:
        with self._transaction() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS combination_reviews (
                    review_key TEXT PRIMARY KEY,
                    run_name TEXT NOT NULL,
                    combination_id TEXT NOT NULL,
                    review_state TEXT NOT NULL,
                    decision_source TEXT,
                    manual_decision TEXT,
                    rationale TEXT,
                    custom_final_constraint TEXT,
                    runtime_recommendation TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS counter_example_cases (
                    case_id TEXT PRIMARY KEY,
                    review_key TEXT NOT NULL,
                    case_state TEXT NOT NULL,
                    request TEXT NOT NULL,
                    request_private TEXT,
                    request_display TEXT,
                    source TEXT NOT NULL,
                    rationale TEXT,
                    generation_id TEXT,
                    target_truth_vector TEXT,
                    risk TEXT,
                    expected_observation TEXT,
                    validation_error TEXT,
                    planner_version TEXT,
                    source_metadata TEXT,
                    runtime_verdict TEXT,
                    runtime_result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(review_key) REFERENCES combination_reviews(review_key)
                );
                CREATE TABLE IF NOT EXISTS counter_example_runs (
                    run_id TEXT PRIMARY KEY,
                    review_key TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    runtime_verdict TEXT,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS combination_review_events (
                    event_id TEXT PRIMARY KEY,
                    review_key TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(review_key, sequence)
                );
                CREATE TABLE IF NOT EXISTS combination_review_idempotency (
                    review_key TEXT NOT NULL,
                    action TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    result_metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(review_key, action, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS idx_combination_reviews_run_name
                    ON combination_reviews(run_name);
                CREATE INDEX IF NOT EXISTS idx_counter_example_cases_review_key
                    ON counter_example_cases(review_key);
                CREATE INDEX IF NOT EXISTS idx_combination_review_events_review_sequence
                    ON combination_review_events(review_key, sequence);
                """
            )
            _add_column_if_missing(conn, "counter_example_cases", "generation_id", "TEXT")
            _add_column_if_missing(
                conn, "counter_example_cases", "request_private", "TEXT"
            )
            _add_column_if_missing(
                conn, "counter_example_cases", "request_display", "TEXT"
            )
            _add_column_if_missing(
                conn, "counter_example_cases", "target_truth_vector", "TEXT"
            )
            _add_column_if_missing(conn, "counter_example_cases", "risk", "TEXT")
            _add_column_if_missing(
                conn, "counter_example_cases", "expected_observation", "TEXT"
            )
            _add_column_if_missing(
                conn, "counter_example_cases", "validation_error", "TEXT"
            )
            _add_column_if_missing(
                conn, "counter_example_cases", "planner_version", "TEXT"
            )
            _add_column_if_missing(
                conn, "counter_example_cases", "source_metadata", "TEXT"
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_counter_example_cases_generation_id
                    ON counter_example_cases(review_key, generation_id)
                """
            )
            _backfill_request_columns(conn)


def review_key(
    *,
    run_name: str,
    operation_id: str,
    property_path: str,
    static_constraint: str | None,
    dynamic_constraint: str | None,
) -> str:
    raw = "\x1f".join(
        [
            run_name,
            operation_id,
            property_path,
            static_constraint or "",
            dynamic_constraint or "",
        ]
    )
    return f"crv_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def _insert_event(
    conn: sqlite3.Connection,
    *,
    review_key: str,
    event_type: str,
    metadata: JsonValue,
) -> None:
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) AS sequence FROM combination_review_events WHERE review_key = ?",
        (review_key,),
    ).fetchone()
    sequence = int(row["sequence"]) + 1
    conn.execute(
        """
        INSERT INTO combination_review_events (
            event_id, review_key, sequence, event_type, metadata, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            f"cre_{uuid.uuid4().hex}",
            review_key,
            sequence,
            event_type,
            _to_json(metadata),
            _now(),
        ),
    )


def _review_from_row(row: sqlite3.Row) -> CombinationReview:
    return CombinationReview(
        run_name=str(row["run_name"]),
        combination_id=str(row["combination_id"]),
        review_key=str(row["review_key"]),
        review_state=str(row["review_state"]),
        decision_source=row["decision_source"],
        manual_decision=row["manual_decision"],
        rationale=row["rationale"],
        custom_final_constraint=row["custom_final_constraint"],
        runtime_recommendation=row["runtime_recommendation"],
        created_at=_from_text(str(row["created_at"])),
        updated_at=_from_text(str(row["updated_at"])),
    )


def _case_from_row(row: sqlite3.Row) -> CounterExampleCase:
    request_private = _json_or_none(row["request_private"]) or json.loads(str(row["request"]))
    request_display = _json_or_none(row["request_display"]) or json.loads(str(row["request"]))
    return CounterExampleCase(
        case_id=str(row["case_id"]),
        review_key=str(row["review_key"]),
        case_state=str(row["case_state"]),
        request=request_private,
        request_display=request_display,
        source=str(row["source"]),
        rationale=row["rationale"],
        generation_id=row["generation_id"],
        target_truth_vector=_json_or_none(row["target_truth_vector"]),
        risk=row["risk"],
        expected_observation=row["expected_observation"],
        validation_error=_json_or_none(row["validation_error"]),
        planner_version=row["planner_version"],
        source_metadata=_json_or_none(row["source_metadata"]),
        runtime_verdict=row["runtime_verdict"],
        runtime_result=_json_or_none(row["runtime_result"]),
        created_at=_from_text(str(row["created_at"])),
        updated_at=_from_text(str(row["updated_at"])),
    )


def _event_from_row(row: sqlite3.Row) -> CombinationReviewEvent:
    return CombinationReviewEvent(
        event_id=str(row["event_id"]),
        review_key=str(row["review_key"]),
        sequence=int(row["sequence"]),
        event_type=str(row["event_type"]),
        metadata=json.loads(str(row["metadata"])),
        created_at=_from_text(str(row["created_at"])),
    )


def _to_json(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_or_none(value: Any) -> JsonValue | None:
    if value is None:
        return None
    return json.loads(str(value))


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if column not in {str(row["name"]) for row in rows}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _backfill_request_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT case_id, request, request_private, request_display, validation_error
        FROM counter_example_cases
        """
    ).fetchall()
    for row in rows:
        request = json.loads(str(row["request"]))
        request_private = _json_or_none(row["request_private"]) or request
        request_display = _json_or_none(row["request_display"]) or request
        validation_error = _json_or_none(row["validation_error"])
        if has_redacted_literal(request_private):
            validation_error = merge_validation_errors(
                validation_error,
                redacted_executable_validation_error(),
            )
        conn.execute(
            """
            UPDATE counter_example_cases
            SET request_private = ?, request_display = ?, validation_error = ?
            WHERE case_id = ?
            """,
            (
                _to_json(request_private),
                _to_json(request_display),
                _to_json(validation_error) if validation_error is not None else None,
                row["case_id"],
            ),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)
