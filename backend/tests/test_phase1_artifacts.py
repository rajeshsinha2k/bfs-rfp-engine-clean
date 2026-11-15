from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from pptx import Presentation

from backend.app.main import app


def test_phase1_default_deal_brief_and_questionnaire():
    """Verifies default corporate PPTX and XLSX generation when no sample templates are fed."""
    with TestClient(app) as client:
        res = client.post(
            "/api/rfps/new",
            data={"client_name": "Meridian Bank", "detected_language": "en"},
            files={
                "file": (
                    "req.md",
                    b"# Payments Scope\n1. Support ISO 20022 instant clearing.\n# Security\n2. Enforce SOC2 Type II and TLS 1.3.",
                    "text/markdown",
                )
            },
        )
        assert res.status_code == 200
        body = res.json()
        rfp_id = body["rfp_id"]
        state = body["state"]

        assert state["workflow_status"] == "PAUSED_HITL_1"
        assert state["deal_brief_meta"]["mode"] == "DEFAULT_CORPORATE"
        assert state["questionnaire_meta"]["mode"] == "DEFAULT_CORPORATE"

        # Verify both artifacts are downloadable via LAN endpoint
        dl_ppt = client.get(f"/api/rfps/{rfp_id}/download/deal_brief_pptx")
        assert dl_ppt.status_code == 200
        assert len(dl_ppt.content) > 500

        dl_xls = client.get(f"/api/rfps/{rfp_id}/download/questionnaire_xlsx")
        assert dl_xls.status_code == 200
        assert len(dl_xls.content) > 500


def test_phase1_sample_driven_ppt_and_excel_population(tmp_path):
    """Verifies that feeding existing Deal Brief PPTX and Questionnaire XLSX preserves static headings/columns."""
    # 1. Build a sample Deal Brief PPTX with custom static headings & subheadings
    sample_ppt = tmp_path / "sample_brief.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Payments & Clearing Architecture"
    tf = slide.placeholders[1].text_frame
    tf.text = "Static Subheading: Settlement Rail Readiness"
    prs.save(str(sample_ppt))

    # 2. Build a sample Questionnaire XLSX with custom columns & static classification row
    sample_xls = tmp_path / "sample_questionnaire.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Custom_BFS_Matrix"
    ws.append(["Ref #", "Static Classification", "Module Heading", "Client Requirement", "Clarification Status"])
    ws.append(["STATIC-01", "Tier-1 Core Payments", "Reference Baseline", "Pre-existing static benchmark row", "Baseline"])
    wb.save(str(sample_xls))

    # 3. Submit RFP with both sample templates attached
    with TestClient(app) as client:
        with open(sample_ppt, "rb") as f_ppt, open(sample_xls, "rb") as f_xls:
            res = client.post(
                "/api/rfps/new",
                data={"client_name": "Banco Horizonte", "detected_language": "en"},
                files={
                    "file": (
                        "requirements.md",
                        b"# Payments & Clearing\n1. Must process ISO 20022 pacs.008 under 200ms.\n2. Custom legacy mainframe adapter required.",
                        "text/markdown",
                    ),
                    "sample_deal_brief_ppt": ("sample_brief.pptx", f_ppt, "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                    "sample_questionnaire_excel": ("sample_questionnaire.xlsx", f_xls, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                },
            )

        assert res.status_code == 200
        state = res.json()["state"]
        assert state["deal_brief_meta"]["mode"] == "SAMPLE_DRIVEN"
        assert state["questionnaire_meta"]["mode"] == "SAMPLE_DRIVEN"
        assert state["questionnaire_meta"]["sheet_name"] == "Custom_BFS_Matrix"
        assert state["questionnaire_meta"]["static_rows_preserved"] == 1

        # Inspect generated Excel file to verify static row + populated requirement rows coexist
        out_xls_path = state["phase1_artifact_paths"]["questionnaire_xlsx"]
        out_wb = load_workbook(out_xls_path)
        out_ws = out_wb["Custom_BFS_Matrix"]
        rows = list(out_ws.iter_rows(values_only=True))
        assert rows[0][1] == "Static Classification"
        assert rows[1][0] == "STATIC-01"
        assert any("ISO 20022" in str(r) for r in rows[2:])
