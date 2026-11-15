# Enhancement 5: Cross-Language Localization & Automated Numeric/Table Parity QA Gate

## Overview & Context
Upgrade `backend/app/security/privacy_and_translation.py` and the Phase 3/Phase 5 QA pipeline so multi-language RFPs (`pt`, `es`, `de`, `fr`) generate distinct localized section labels/headers in `native` while enforcing strict **Numeric, Currency, PII Token & Table Parity** (`validate_cross_language_parity`). Wire this validator into Phase 5 QA so any mismatch between English Core and Native Mirror halts assembly (`HTTP 422`) and logs a QA failure in `immutable_audit_log`, plus expose `POST /api/qa/verify-parity` and display a parity status badge in `frontend/src/App.tsx`.

## Constraints
* **Deterministic & offline:** Must run locally without paid cloud translation APIs.
* **Preserve PII tokens:** Tokens like `<BANK_PII_IBAN_1>` must pass through untouched without triggering numeric mismatch errors.
* **English audit trail:** All QA pass/fail records in `immutable_audit_log` must be written in English.

## Required Deliverables & Test Cases
1. Implement `validate_cross_language_parity()` in `backend/app/security/privacy_and_translation.py`, wire localized payloads and the Phase 5 QA gate in `backend/app/agents/graph.py`, expose `POST /api/qa/verify-parity` in `backend/app/main.py`, and update `frontend/src/App.tsx`.
2. Write **5 distinct `pytest` test cases** in **`backend/tests/test_language_parity_qa.py`**:
   * `test_localized_portuguese_workflow_preserves_numeric_parity`
   * `test_drifted_tco_amount_fails_parity_validator`
   * `test_drifted_sla_percentage_fails_parity_validator`
   * `test_markdown_table_row_count_mismatch_detected`
   * `test_pii_redaction_tokens_survive_parity_validation`

## How to Judge Completion
* **Where to Look:** `backend/app/security/privacy_and_translation.py`, `backend/app/agents/graph.py`, `backend/app/main.py`, `frontend/src/App.tsx`, and `backend/tests/test_language_parity_qa.py`.
* **What to Look For:**
  * Running a Portuguese (`pt`) RFP produces localized labels in the Native Mirror pane while keeping all numbers, SLA percentages, and TCO figures identical to English Core.
  * Drifted currency/SLA numbers or mismatched Markdown table row counts fail `validate_cross_language_parity()` and block Phase 5 assembly with an English audit log entry, while `<BANK_PII_...>` tokens pass cleanly.
* **What Counts as a Pass:**
  * Executing `source ./startVenv.sh && pytest -v` passes all 14 tests (9 existing + 5 new) cleanly, and `cd frontend && npm run build` exits with code `0`.
