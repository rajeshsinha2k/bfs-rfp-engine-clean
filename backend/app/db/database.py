import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "rfp_engine.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema_sql)


def append_audit_log(
    rfp_id: str,
    actor_identity: str,
    action_type: str,
    phase_context: int,
    payload_english: Dict[str, Any],
) -> str:
    """Rule 3: Appends an immutable, SHA-256 hash-chained English audit record."""
    payload_str = json.dumps(payload_english, sort_keys=True, ensure_ascii=True)

    with get_connection() as conn:
        last_row = conn.execute(
            "SELECT record_hash FROM immutable_audit_log ORDER BY audit_id DESC LIMIT 1"
        ).fetchone()
        previous_hash = last_row["record_hash"] if last_row else "0" * 64

        raw_block = f"{previous_hash}|{rfp_id}|{actor_identity}|{action_type}|{phase_context}|{payload_str}"
        record_hash = hashlib.sha256(raw_block.encode("utf-8")).hexdigest()

        conn.execute(
            """
            INSERT INTO immutable_audit_log
            (rfp_id, actor_identity, action_type, phase_context, payload_english_json, previous_hash, record_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rfp_id,
                actor_identity,
                action_type,
                phase_context,
                payload_str,
                previous_hash,
                record_hash,
            ),
        )
        conn.commit()
    return record_hash
