import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import append_audit_log, get_connection


def test_immutable_audit_log_blocks_tampering():
    """Governance Rule 3: Verifies SHA-256 hash chaining and UPDATE/DELETE triggers."""
    h1 = append_audit_log("RFP-2026-900-V1.0", "auditor@corp.local", "TEST_EVENT_1", 1, {"step": 1})
    h2 = append_audit_log("RFP-2026-900-V1.0", "auditor@corp.local", "TEST_EVENT_2", 1, {"step": 2})
    assert len(h1) == 64
    assert h1 != h2

    with get_connection() as conn:
        row = conn.execute("SELECT previous_hash, record_hash FROM immutable_audit_log WHERE audit_id = 2").fetchone()
        assert row["previous_hash"] == h1
        assert row["record_hash"] == h2

        with pytest.raises(sqlite3.IntegrityError, match="Audit log is immutable: UPDATE forbidden"):
            conn.execute("UPDATE immutable_audit_log SET action_type = 'TAMPERED' WHERE audit_id = 1")

        with pytest.raises(sqlite3.IntegrityError, match="Audit log is immutable: DELETE forbidden"):
            conn.execute("DELETE FROM immutable_audit_log WHERE audit_id = 1")


def test_hitl_1_no_go_archives_rfp():
    """Phase 1 -> HITL 1 [NO-GO]: Ensures workflow halts and archives cleanly."""
    with TestClient(app) as client:
        res_start = client.post(
            "/api/rfps/new",
            data={"client_name": "Banco Sul", "detected_language": "pt"},
            files={"file": ("rfp.txt", b"# Core Banking\n1. Support PIX?", "text/plain")},
        )
        assert res_start.status_code == 200
        rfp_id = res_start.json()["rfp_id"]
        assert res_start.json()["state"]["workflow_status"] == "PAUSED_HITL_1"

        res_nogo = client.post(f"/api/rfps/{rfp_id}/hitl", json={"action_id": "NO_GO"})
        assert res_nogo.status_code == 200
        assert res_nogo.json()["state"]["workflow_status"] == "NO_GO"


def test_full_five_phase_go_to_completion():
    """End-to-End: Phase 1 -> [GO] -> Phases 2-4 -> [HITL 2] -> Phase 5 Final Package."""
    with TestClient(app) as client:
        res1 = client.post(
            "/api/rfps/new",
            data={"client_name": "Banco Nacional", "detected_language": "pt"},
            files={"file": ("rfp.txt", b"# Core Banking\n1. Support ISO 20022?\n2. Custom legacy migration?", "text/plain")},
        )
        assert res1.status_code == 200
        rfp_id = res1.json()["rfp_id"]
        assert res1.json()["state"]["workflow_status"] == "PAUSED_HITL_1"

        # Checkpoint 1: Click [GO]
        res2 = client.post(f"/api/rfps/{rfp_id}/hitl", json={"action_id": "GO"})
        assert res2.status_code == 200
        state2 = res2.json()["state"]
        assert state2["workflow_status"] == "PAUSED_HITL_2"
        assert len(state2["question_slices"]) == 2
        assert len(state2["clarification_log"]) == 1
        assert state2["tco_model"]["three_year_tco"] > 0

        # Checkpoint 2: Approve Red Team & Legal Review
        res3 = client.post(f"/api/rfps/{rfp_id}/hitl", json={"action_id": "APPROVE_HITL_2"})
        assert res3.status_code == 200
        state3 = res3.json()["state"]
        assert state3["workflow_status"] == "COMPLETED"
        assert set(state3["final_package_paths"].keys()) == {
            "template_applied",
            "native_pdf",
            "english_mirror_pdf",
            "commercial_xlsx",
            "c_suite_pptx",
        }
