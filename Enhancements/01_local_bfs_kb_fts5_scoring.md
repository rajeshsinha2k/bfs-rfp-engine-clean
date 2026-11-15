# Enhancement 1: Local BFS Knowledge Base Indexing (SQLite FTS5) & Dynamic Question Scoring

## Overview & Context
Right now, `document_slicer_tool` in `backend/app/agents/tools.py` assigns static confidence scores when slicing an incoming RFP. We need a lightweight, local-first **SQLite FTS5 Knowledge Base** (`backend/app/db/kb_store.py`) so we can ingest BFS product and compliance capability sheets (Markdown/text), index them by heading, and score incoming RFP questions dynamically using BM25/keyword relevance. Matched capability snippets should flow through as citations in the Phase 3 Pre-Review Dossier.

## Constraints
* **Keep it local and zero-cost:** Use Python's built-in `sqlite3` FTS5 virtual tables only. Do not add external vector databases, embedding APIs, or non-permissive libraries.
* **Respect test isolation:** Ensure all queries in `kb_store.py` use `get_connection()` so `backend/tests/conftest.py` (`DB_PATH` monkeypatch) stays completely isolated from `backend/rfp_engine.db`.
* **English audit trail:** Log all KB indexing and confidence-scoring summaries to `immutable_audit_log` strictly in English via `append_audit_log()`.

## Required Deliverables & Test Cases
1. Implement `backend/app/db/kb_store.py` and update `backend/app/db/schema.sql`, `backend/app/agents/tools.py`, `backend/app/agents/graph.py`, `backend/app/main.py` (`POST /api/kb/ingest`, `GET /api/kb/articles`), `frontend/src/types.ts`, and `frontend/src/App.tsx`.
2. Write **5 distinct `pytest` test cases** in **`backend/tests/test_kb_fts5.py`**:
   * `test_kb_ingest_splits_headings_and_indexes_fts5`
   * `test_high_confidence_requirement_bypasses_clarification_log`
   * `test_low_confidence_requirement_routes_to_clarification_log`
   * `test_phase3_dossier_includes_matched_kb_citations`
   * `test_empty_kb_graceful_fallback_without_errors`

## How to Judge Completion
* **Where to Look:** `backend/app/db/schema.sql`, `backend/app/db/kb_store.py`, `backend/app/agents/tools.py`, `backend/app/agents/graph.py`, `backend/app/main.py`, `frontend/src/App.tsx`, and `backend/tests/test_kb_fts5.py`.
* **What to Look For:**
  * `kb_store.py` uses `sqlite3` FTS5 virtual tables (`bfs_kb_fts`) and calls `get_connection()` without hardcoding `backend/rfp_engine.db`.
  * Ingesting a product doc covering ISO 20022/SOC2 scores matching RFP questions `>= 0.75` (bypassing `clarification_log` and attaching citations in Phase 3), while undocumented requirements score `< 0.75` and enter `clarification_log`.
* **What Counts as a Pass:**
  * Executing `source ./startVenv.sh && pytest -v` passes all 14 tests (9 existing + 5 new) with zero modifications to existing test assertions.
  * Executing `cd frontend && npm run build` exits with code `0`.
