# Enhancement 6: Policy-Driven Compliance Guardrails & Masked Violation Quarantine Log

## Overview & Context
Refactor `backend/app/security/guardrails.py` from hardcoded lists into a **Policy-Driven Compliance Guardrail Engine** backed by an externalized JSON policy file (`backend/app/security/policy_config.json`) and a SQLite **`security_quarantine_log`** table. Enforce guardrails during Phase 3 and Phase 5 generation, mask leaked secrets before logging, expose `GET /api/security/policy`, `POST /api/security/policy`, and `GET /api/security/violations` in `backend/app/main.py`, and render a compliance quarantine alert banner in `frontend/src/App.tsx`.

## Constraints
* **Never store raw secrets:** Mask leaked API keys/tokens (e.g., `sk-live-***`) before writing to `security_quarantine_log` or `immutable_audit_log`.
* **Test isolation for policy config:** Allow overriding the policy file path in tests so `pytest` never mutates the live `policy_config.json`.
* **English audit trail:** Log every policy update and quarantine event via `append_audit_log()` in English.

## Required Deliverables & Test Cases
1. Create `backend/app/security/policy_config.json`, refactor `backend/app/security/guardrails.py`, add `security_quarantine_log` to `backend/app/db/schema.sql`, enforce guardrails in `backend/app/agents/graph.py`, add admin endpoints in `backend/app/main.py`, and update `frontend/src/App.tsx`.
2. Write **5 distinct `pytest` test cases** in **`backend/tests/test_guardrail_policies.py`**:
   * `test_dynamic_policy_update_blocks_newly_added_competitor`
   * `test_secret_leak_masked_in_security_quarantine_log`
   * `test_allowlisted_central_bank_and_cloud_urls_pass`
   * `test_phase3_blocks_and_quarantines_policy_violation`
   * `test_invalid_policy_payload_rejected_with_422`

## How to Judge Completion
* **Where to Look:** `backend/app/security/policy_config.json`, `backend/app/security/guardrails.py`, `backend/app/db/schema.sql`, `backend/app/agents/graph.py`, `backend/app/main.py`, `frontend/src/App.tsx`, and `backend/tests/test_guardrail_policies.py`.
* **What to Look For:**
  * Adding a competitor via `POST /api/security/policy` blocks that competitor on the next Phase 3 run without restarting the server, while malformed updates return `HTTP 422`.
  * Leaked secrets are masked (`sk-live-***`) in `security_quarantine_log`, and allowlisted regulatory/cloud URLs pass cleanly.
* **What Counts as a Pass:**
  * Executing `source ./startVenv.sh && pytest -v` passes all 14 tests (9 existing + 5 new) cleanly, and `cd frontend && npm run build` exits with code `0`.
