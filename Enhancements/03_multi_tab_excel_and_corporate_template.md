# Enhancement 3: Multi-Tab Excel Introspection & Custom Phase 5 Corporate PPTX Template Wiring

## Overview & Context
In Phase 1, `build_questionnaire_excel()` in `backend/app/agents/phase1_artifacts.py` currently inspects only `wb.active` (the first worksheet). Upgrade it to iterate across **all worksheets** in a multi-tab `.xlsx` workbook, preserve each tab's headers and static baseline rows, and route extracted RFP items to the best-matching tab by sheet-title/domain affinity. Additionally, wire an optional Phase 5 corporate `.pptx` template upload (`custom_submission_template_ppt`) through `POST /api/rfps/new`, `graph.py`, `document_publisher_tool()`, and `frontend/src/App.tsx`.

## Constraints
* **Workspace path isolation:** Reference `config.WORKSPACES_DIR` dynamically so `conftest.py` temporary directory fixtures remain isolated.
* **Preserve static content:** Never overwrite existing headers or static baseline rows in any tab of a sample `.xlsx` or slides of a custom `.pptx`.
* **Backward compatibility:** Single-tab `.xlsx` samples and `DEFAULT_CORPORATE` fallback mode must keep working identically using permissive OSS libraries (`openpyxl`, `python-pptx`).

## Required Deliverables & Test Cases
1. Update `backend/app/agents/phase1_artifacts.py`, `backend/app/agents/tools.py`, `backend/app/agents/graph.py`, `backend/app/main.py`, and `frontend/src/App.tsx`.
2. Write **5 distinct `pytest` test cases** in **`backend/tests/test_multi_sheet_templates.py`**:
   * `test_multi_sheet_excel_routes_items_to_matching_tabs`
   * `test_multi_sheet_preserves_headers_and_static_rows_per_tab`
   * `test_questionnaire_meta_reports_per_sheet_breakdown`
   * `test_custom_phase5_corporate_pptx_template_preserved`
   * `test_fallback_when_sample_excel_has_unmatched_tab_names`

## How to Judge Completion
* **Where to Look:** `backend/app/agents/phase1_artifacts.py`, `backend/app/agents/tools.py`, `backend/app/agents/graph.py`, `backend/app/main.py`, `frontend/src/App.tsx`, and `backend/tests/test_multi_sheet_templates.py`.
* **What to Look For:**
  * Uploading a 3-tab `.xlsx` (*Payments*, *InfoSec*, *Cloud*) routes items to matching tabs while keeping pre-existing headers and static baseline rows intact across every worksheet.
  * Uploading a custom Phase 5 `.pptx` template produces a final `*_Executive_Pitch.pptx` that retains the custom cover slide and sets `template_applied` accurately.
* **What Counts as a Pass:**
  * Executing `source ./startVenv.sh && pytest -v` passes all 14 tests (9 existing + 5 new) cleanly, and `cd frontend && npm run build` exits with code `0`.
