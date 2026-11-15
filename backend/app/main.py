from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.agents.graph import rfp_orchestrator
from backend.app.agents.tools import generate_unique_rfp_id
from backend.app.config import WORKSPACES_DIR, settings
from backend.app.db.database import append_audit_log, get_connection, init_db
from backend.app.models.schemas import WorkflowStatus
from backend.app.security.ingestion import parse_document_to_markdown
from backend.app.security.privacy_and_translation import (
    bridge_native_to_english,
    redact_banking_pii,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Autonomous BFS Pre-Sales RFP Engine (LAN Host)",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HITLDecisionRequest(BaseModel):
    action_id: str
    actor_identity: str = settings.corporate_user_default
    feedback: Optional[str] = None


@app.get("/api/health")
def health_check():
    return {"status": "online", "mode": "LAN-First Local Host"}


@app.get("/api/rfps")
def list_existing_rfps():
    """Phase 1 Gateway: Returns historical matrix of existing RFPs & states to resume from."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT rfp_id, client_name_redacted, detected_language, current_phase, workflow_status, updated_at FROM rfp_projects ORDER BY updated_at DESC"
        ).fetchall()
    return {"rfps": [dict(r) for r in rows]}


@app.post("/api/rfps/new")
async def start_new_rfp(
    client_name: str = Form(...),
    detected_language: str = Form("en"),
    actor_identity: str = Form(settings.corporate_user_default),
    custom_template_path: Optional[str] = Form(None),
    file: UploadFile = File(...),
    sample_deal_brief_ppt: Optional[UploadFile] = File(None),
    sample_questionnaire_excel: Optional[UploadFile] = File(None),
):
    """
    Phase 1 Gateway: Issues permanent RFP ID, ingests primary requirement document + optional
    sample Deal Brief (.pptx) and Questionnaire (.xlsx), and pauses at Paused [HITL 1].
    """
    rfp_id = generate_unique_rfp_id()
    workspace = WORKSPACES_DIR / rfp_id
    workspace.mkdir(parents=True, exist_ok=True)

    saved_file = workspace / (file.filename or "rfp_input.txt")
    saved_file.write_bytes(await file.read())

    sample_ppt_saved: Optional[str] = None
    if sample_deal_brief_ppt and sample_deal_brief_ppt.filename:
        ppt_dest = workspace / f"sample_{sample_deal_brief_ppt.filename}"
        ppt_dest.write_bytes(await sample_deal_brief_ppt.read())
        sample_ppt_saved = str(ppt_dest)

    sample_xls_saved: Optional[str] = None
    if sample_questionnaire_excel and sample_questionnaire_excel.filename:
        xls_dest = workspace / f"sample_{sample_questionnaire_excel.filename}"
        xls_dest.write_bytes(await sample_questionnaire_excel.read())
        sample_xls_saved = str(xls_dest)

    raw_markdown = parse_document_to_markdown(saved_file)
    if len(raw_markdown.strip()) < 15:
        raw_markdown = (
            f"# {client_name} Core Banking RFP\n"
            "1. Confirm ISO 20022 real-time payment support?\n"
            "2. Describe custom legacy core migration strategy?"
        )

    redacted_markdown, _ = redact_banking_pii(raw_markdown)
    english_markdown = bridge_native_to_english(redacted_markdown, detected_language)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO rfp_projects
            (rfp_id, client_name_redacted, detected_language, current_phase, workflow_status, custom_template_path, workspace_dir, created_by_user)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (
                rfp_id,
                client_name,
                detected_language,
                WorkflowStatus.RUNNING.value,
                custom_template_path,
                str(workspace),
                actor_identity,
            ),
        )
        conn.commit()

    append_audit_log(
        rfp_id,
        actor_identity,
        "NEW_RFP_CREATED",
        1,
        {
            "filename": file.filename,
            "language": detected_language,
            "has_sample_ppt": bool(sample_ppt_saved),
            "has_sample_excel": bool(sample_xls_saved),
        },
    )

    config = {"configurable": {"thread_id": rfp_id}}
    initial_state = {
        "rfp_id": rfp_id,
        "client_name": client_name,
        "actor_identity": actor_identity,
        "detected_language": detected_language,
        "raw_markdown": english_markdown,
        "custom_template_path": custom_template_path,
        "sample_ppt_path": sample_ppt_saved,
        "sample_excel_path": sample_xls_saved,
        "current_phase": 1,
        "workflow_status": WorkflowStatus.RUNNING.value,
        "chat_events": [],
    }

    result = rfp_orchestrator.invoke(initial_state, config=config)
    return {"rfp_id": rfp_id, "state": result}


@app.post("/api/rfps/{rfp_id}/hitl")
def submit_hitl_decision(rfp_id: str, payload: HITLDecisionRequest):
    """Resumes LangGraph execution from Paused [HITL 1] or Paused [HITL 2] upon user button click."""
    config = {"configurable": {"thread_id": rfp_id}}
    snapshot = rfp_orchestrator.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail=f"RFP thread {rfp_id} not found")

    append_audit_log(
        rfp_id,
        payload.actor_identity,
        f"HITL_BUTTON_{payload.action_id}",
        snapshot.values.get("current_phase", 1),
        {"action_id": payload.action_id, "feedback": payload.feedback},
    )

    if payload.action_id in ("GO", "NO_GO"):
        rfp_orchestrator.update_state(config, {"hitl_1_decision": payload.action_id})
        result = rfp_orchestrator.invoke(None, config=config)
        return {"rfp_id": rfp_id, "state": result}

    if payload.action_id == "APPROVE_HITL_2":
        rfp_orchestrator.update_state(
            config, {"hitl_2_approved": True, "hitl_2_feedback": payload.feedback}
        )
        result = rfp_orchestrator.invoke(None, config=config)
        return {"rfp_id": rfp_id, "state": result}

    if payload.action_id == "AUTHORIZE_TRANSMISSION":
        return {
            "rfp_id": rfp_id,
            "status": "TRANSMISSION_AUTHORIZED",
            "message": f"Executive transmission authorized and logged for {rfp_id}.",
        }

    raise HTTPException(status_code=400, detail=f"Unknown action_id: {payload.action_id}")


@app.get("/api/rfps/{rfp_id}/download/{artifact_key}")
def download_rfp_artifact(rfp_id: str, artifact_key: str, actor_identity: str = settings.corporate_user_default):
    """Allows Windows Desktop and Mobile LAN clients to download generated PPTX, XLSX, and PDF artifacts."""
    config = {"configurable": {"thread_id": rfp_id}}
    snapshot = rfp_orchestrator.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail=f"RFP thread {rfp_id} not found")

    state_vals = snapshot.values
    all_paths = {}
    all_paths.update(state_vals.get("phase1_artifact_paths", {}))
    all_paths.update(state_vals.get("final_package_paths", {}))

    target = all_paths.get(artifact_key)
    if not target or not Path(target).exists():
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_key}' not found for {rfp_id}")

    append_audit_log(
        rfp_id,
        actor_identity,
        "ARTIFACT_DOWNLOADED",
        state_vals.get("current_phase", 1),
        {"artifact_key": artifact_key, "filename": Path(target).name},
    )
    return FileResponse(path=target, filename=Path(target).name)
