# Enhancement 4: Historical RFP Resume, Workspace Explorer & SHA-256 Audit Chain Verifier

## Overview & Context
Currently, `[Existing RFP]` in the UI renders a static table from `rfp_projects` without allowing users to click an RFP to restore its chat timeline, resume a paused `PAUSED_HITL_1` or `PAUSED_HITL_2` session, browse generated workspace files, or verify its cryptographic audit chain. Add `GET /api/rfps/{rfp_id}/state`, `GET /api/rfps/{rfp_id}/artifacts`, and `GET /api/rfps/{rfp_id}/audit/verify`, and make rows in the Historical RFP Matrix clickable in `frontend/src/App.tsx`.

## Constraints
* **Do not re-execute completed graph nodes:** Read persisted state directly via `rfp_orchestrator.get_state({"configurable": {"thread_id": rfp_id}})`.
* **Exact SHA-256 chain formula:** Recompute `SHA256(previous_hash|rfp_id|actor|action|phase|payload)` across every row in `immutable_audit_log` in `audit_id` order.
* **Clean error handling:** Unknown `rfp_id` lookups must return `HTTP 404`.

## Required Deliverables & Test Cases
1. Implement `verify_audit_chain()` in `backend/app/db/database.py`, add routes in `backend/app/main.py`, and update `frontend/src/types.ts` and `frontend/src/App.tsx`.
2. Write **5 distinct `pytest` test cases** in **`backend/tests/test_resume_and_audit_verify.py`**:
   * `test_get_persisted_state_returns_hitl1_checkpoint`
   * `test_resume_paused_rfp_via_state_and_hitl_post`
   * `test_workspace_artifacts_endpoint_lists_generated_files`
   * `test_audit_chain_verification_succeeds_across_5_phases`
   * `test_unknown_rfp_id_returns_404_cleanly`

## How to Judge Completion
* **Where to Look:** `backend/app/db/database.py`, `backend/app/main.py`, `frontend/src/App.tsx`, `frontend/src/types.ts`, and `backend/tests/test_resume_and_audit_verify.py`.
* **What to Look For:**
  * Reloading the browser, clicking `[Existing RFP]`, and selecting a `PAUSED_HITL_1` RFP restores its full `chat_events` timeline and lets the user click `[GO]` to complete Phases 2–5.
  * `GET /api/rfps/{rfp_id}/audit/verify` returns `valid: true` with all phase audit records listed in chronological order, and unknown IDs return `HTTP 404`.
* **What Counts as a Pass:**
  * Executing `source ./startVenv.sh && pytest -v` passes all 14 tests (9 existing + 5 new) cleanly, and `cd frontend && npm run build` exits with code `0`.
