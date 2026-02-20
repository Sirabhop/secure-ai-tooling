"""Persistence helpers for AI inventory and self-assessment records."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.db import get_connection, is_database_ready as db_ready

logger = logging.getLogger(__name__)


def is_database_ready() -> bool:
    """Return True when runtime is ready to use PostgreSQL persistence."""
    return db_ready()


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _generate_assessment_id() -> str:
    return f"ASMT-{uuid.uuid4().hex[:10].upper()}"


def save_ai_inventory_submission(data: Dict[str, Any], repeat_blocks: Dict[str, List[Dict[str, Any]]]) -> str:
    """Insert or update AI inventory submission, returning its use_case_id."""
    payload = dict(data or {})
    use_case_id = str(payload.get("useCaseId") or f"UC-{uuid.uuid4().hex[:8].upper()}")
    payload["useCaseId"] = use_case_id

    rows = repeat_blocks or {}

    sql = """
        INSERT INTO ai_inventory_submissions (
            use_case_id,
            use_case_name,
            business_unit,
            model_creator,
            model_usage,
            payload,
            repeat_blocks
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
        ON CONFLICT (use_case_id) DO UPDATE
        SET
            use_case_name = EXCLUDED.use_case_name,
            business_unit = EXCLUDED.business_unit,
            model_creator = EXCLUDED.model_creator,
            model_usage = EXCLUDED.model_usage,
            payload = EXCLUDED.payload,
            repeat_blocks = EXCLUDED.repeat_blocks,
            updated_at = NOW()
        RETURNING use_case_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    use_case_id,
                    payload.get("useCaseName"),
                    payload.get("businessUnit"),
                    payload.get("modelCreator"),
                    payload.get("modelUsage"),
                    json.dumps(payload),
                    json.dumps(rows),
                ),
            )
            row = cur.fetchone()
        conn.commit()

    persisted_id = row["use_case_id"] if row else use_case_id
    logger.info("Saved AI inventory submission id=%s", persisted_id)
    return persisted_id


def load_ai_inventory_submission(use_case_id: str) -> Optional[Dict[str, Any]]:
    """Load an AI inventory submission by its use_case_id."""
    if not use_case_id:
        return None

    sql = """
        SELECT
            use_case_id,
            payload,
            repeat_blocks,
            created_at,
            updated_at
        FROM ai_inventory_submissions
        WHERE use_case_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (use_case_id,))
            row = cur.fetchone()

    if not row:
        return None

    payload = _as_dict(row.get("payload"))
    payload["useCaseId"] = row.get("use_case_id") or payload.get("useCaseId")

    return {
        "use_case_id": row.get("use_case_id"),
        "payload": payload,
        "repeat_blocks": _as_dict(row.get("repeat_blocks")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def save_self_assessment_submission(
    *,
    assessment_id: Optional[str],
    ai_inventory_use_case_id: Optional[str],
    selected_personas: List[str],
    selected_use_cases: List[str],
    answers: Dict[str, Any],
    vayu_result: Dict[str, Any],
    relevant_risks: List[str],
    recommended_controls: List[str],
) -> str:
    """Insert or update self-assessment submission and return its assessment_id."""
    persisted_id = str(assessment_id or _generate_assessment_id())
    payload = {
        "selected_personas": list(selected_personas or []),
        "selected_use_cases": list(selected_use_cases or []),
        "answers": dict(answers or {}),
        "vayu_result": dict(vayu_result or {}),
        "relevant_risks": list(relevant_risks or []),
        "recommended_controls": list(recommended_controls or []),
        "ai_inventory_use_case_id": ai_inventory_use_case_id,
    }

    sql = """
        INSERT INTO self_assessment_submissions (
            assessment_id,
            ai_inventory_use_case_id,
            selected_personas,
            selected_use_cases,
            answers,
            vayu_result,
            relevant_risks,
            recommended_controls,
            payload
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb)
        ON CONFLICT (assessment_id) DO UPDATE
        SET
            ai_inventory_use_case_id = EXCLUDED.ai_inventory_use_case_id,
            selected_personas = EXCLUDED.selected_personas,
            selected_use_cases = EXCLUDED.selected_use_cases,
            answers = EXCLUDED.answers,
            vayu_result = EXCLUDED.vayu_result,
            relevant_risks = EXCLUDED.relevant_risks,
            recommended_controls = EXCLUDED.recommended_controls,
            payload = EXCLUDED.payload,
            updated_at = NOW()
        RETURNING assessment_id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    persisted_id,
                    ai_inventory_use_case_id,
                    list(selected_personas or []),
                    list(selected_use_cases or []),
                    json.dumps(dict(answers or {})),
                    json.dumps(dict(vayu_result or {})),
                    list(relevant_risks or []),
                    list(recommended_controls or []),
                    json.dumps(payload),
                ),
            )
            row = cur.fetchone()
        conn.commit()

    persisted_id = row["assessment_id"] if row else persisted_id
    logger.info("Saved self-assessment submission id=%s", persisted_id)
    return persisted_id


def load_self_assessment_submission(assessment_id: str) -> Optional[Dict[str, Any]]:
    """Load a self-assessment submission by its assessment_id."""
    if not assessment_id:
        return None

    sql = """
        SELECT
            assessment_id,
            ai_inventory_use_case_id,
            selected_personas,
            selected_use_cases,
            answers,
            vayu_result,
            relevant_risks,
            recommended_controls,
            payload,
            created_at,
            updated_at
        FROM self_assessment_submissions
        WHERE assessment_id = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (assessment_id,))
            row = cur.fetchone()

    if not row:
        return None

    return {
        "assessment_id": row.get("assessment_id"),
        "ai_inventory_use_case_id": row.get("ai_inventory_use_case_id"),
        "selected_personas": _as_list(row.get("selected_personas")),
        "selected_use_cases": _as_list(row.get("selected_use_cases")),
        "answers": _as_dict(row.get("answers")),
        "vayu_result": _as_dict(row.get("vayu_result")),
        "relevant_risks": _as_list(row.get("relevant_risks")),
        "recommended_controls": _as_list(row.get("recommended_controls")),
        "payload": _as_dict(row.get("payload")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
