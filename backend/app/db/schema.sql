PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 1. Master RFP Registry & State Machine
CREATE TABLE IF NOT EXISTS rfp_projects (
    rfp_id TEXT PRIMARY KEY,              -- e.g., 'RFP-2026-089-V1.0'
    client_name_redacted TEXT NOT NULL,
    detected_language TEXT NOT NULL,      -- ISO 639-1 ('en', 'pt', 'es', 'de', etc.)
    current_phase INTEGER NOT NULL CHECK (current_phase BETWEEN 1 AND 5),
    workflow_status TEXT NOT NULL,        -- 'RUNNING', 'PAUSED_HITL_1', 'PAUSED_HITL_2', 'NO_GO', 'COMPLETED'
    custom_template_path TEXT NULL,       -- Rule 5 custom template path
    workspace_dir TEXT NOT NULL,
    created_by_user TEXT NOT NULL,        -- Corporate SSO / OS identity
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. Question-by-Question Slices & Dual-Language Artifacts (Phases 2 & 3)
CREATE TABLE IF NOT EXISTS rfp_question_slices (
    slice_id TEXT PRIMARY KEY,
    rfp_id TEXT NOT NULL REFERENCES rfp_projects(rfp_id),
    section_anchor TEXT NOT NULL,
    question_native TEXT NOT NULL,
    question_english TEXT NOT NULL,
    assigned_owner TEXT,
    raci_role TEXT CHECK (raci_role IN ('R', 'A', 'C', 'I') OR raci_role IS NULL),
    kb_confidence_score REAL,             -- < 75.0 triggers Clarification Log
    draft_response_english TEXT,
    draft_response_native TEXT,
    external_citations_json TEXT DEFAULT '[]',
    guardrail_status TEXT DEFAULT 'PENDING'
);

-- 3. Immutable Background Audit Trail Logger (Rule 3)
CREATE TABLE IF NOT EXISTS immutable_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    rfp_id TEXT NOT NULL,
    actor_identity TEXT NOT NULL,
    action_type TEXT NOT NULL,
    phase_context INTEGER NOT NULL,
    payload_english_json TEXT NOT NULL,   -- Strictly English per Rule 2 & Rule 3
    previous_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL
);

-- Enforce Append-Only Immutability
CREATE TRIGGER IF NOT EXISTS prevent_audit_update
BEFORE UPDATE ON immutable_audit_log
BEGIN
    SELECT RAISE(ABORT, 'Audit log is immutable: UPDATE forbidden');
END;

CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
BEFORE DELETE ON immutable_audit_log
BEGIN
    SELECT RAISE(ABORT, 'Audit log is immutable: DELETE forbidden');
END;
