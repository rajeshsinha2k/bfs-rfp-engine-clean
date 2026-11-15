# Enhancement 2: Interactive Clarification Log Gate (`PAUSED_CLARIFICATION`) Before Phase 3

## Overview & Context
Currently, when Phase 2 isolates low-confidence questions (`< 0.75` KB match) into `clarification_log`, LangGraph immediately advances into Phase 3 (`phase_3_generation_node`). Turn the Clarification Log into an interactive **Human-in-the-Loop Clarification Gate (`PAUSED_CLARIFICATION`)**. If Phase 2 finds open clarifications, pause LangGraph before Phase 3 so pre-sales engineers or SMEs can submit client answers (or waive items) in the UI, save them in SQLite, and resume Phase 3–5 with those clarifications incorporated into the technical dossier. If zero low-confidence items exist, bypass the pause and proceed straight to Phase 3.

## Constraints
* **LangGraph resumption mechanics:** Resume interrupted state cleanly via `rfp_orchestrator.update_state(config, ...)` followed by `rfp_orchestrator.invoke(None, config)`.
* **Audit log immutability:** `immutable_audit_log` blocks `UPDATE` and `DELETE` via SQLite triggers; append English audit records via `append_audit_log()`.
* **Preserve existing gates:** `PAUSED_HITL_1` and `PAUSED_HITL_2` must continue operating unchanged.

## Required Deliverables & Test Cases
1. Update `backend/app/models/schemas.py` (`PAUSED_CLARIFICATION`), `backend/app/db/schema.sql` (`clarification_answer`, `clarification_status`), `backend/app/agents/graph.py`, `backend/app/main.py` (`GET`/`POST /api/rfps/{rfp_id}/clarifications`), `frontend/src/types.ts`, and `frontend/src/App.tsx`.
2. Write **5 distinct `pytest` test cases** in **`backend/tests/test_clarification_loop.py`**:
   * `test_pauses_at_clarification_gate_when_low_confidence_exists`
   * `test_partial_clarification_submission_keeps_gate_paused`
   * `test_full_clarification_resolution_resumes_to_hitl_2`
   * `test_clarified_answers_injected_into_phase3_dossier`
   * `test_bypasses_clarification_gate_when_zero_open_items`

## How to Judge Completion
* **Where to Look:** `backend/app/models/schemas.py`, `backend/app/db/schema.sql`, `backend/app/agents/graph.py`, `backend/app/main.py`, `frontend/src/App.tsx`, and `backend/tests/test_clarification_loop.py`.
* **What to Look For:**
  * Clicking `[GO]` on an RFP with `< 0.75` confidence slices transitions to `PAUSED_CLARIFICATION`; submitting answers via `POST /api/rfps/{rfp_id}/clarifications` persists them to `rfp_question_slices`, appends an English audit log entry, resumes execution to `PAUSED_HITL_2`, and embeds the answers in `pre_review_dossier`.
  * RFPs with zero low-confidence items skip `PAUSED_CLARIFICATION` directly to `PAUSED_HITL_2`.
* **What Counts as a Pass:**
  * Executing `source ./startVenv.sh && pytest -v` passes all 14 tests (9 existing + 5 new) cleanly, and `cd frontend && npm run build` exits with code `0`.
