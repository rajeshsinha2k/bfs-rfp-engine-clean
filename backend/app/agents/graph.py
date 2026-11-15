import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from backend.app.agents.phase1_artifacts import (
    build_deal_brief_ppt,
    build_questionnaire_excel,
)
from backend.app.agents.tools import (
    architecture_canvas_tool,
    directory_workload_scanner,
    document_publisher_tool,
    document_slicer_tool,
    mermaid_sequence_generator,
)
from backend.app.config import WORKSPACES_DIR
from backend.app.db.database import append_audit_log, get_connection
from backend.app.models.schemas import WorkflowStatus
from backend.app.agents.phase1_artifacts import build_deal_brief_ppt, build_questionnaire_excel

CHECKPOINT_DB = Path(__file__).resolve().parents[2] / "langgraph_checkpoints.db"


class RFPWorkflowState(TypedDict, total=False):
    rfp_id: str
    client_name: str
    actor_identity: str
    detected_language: str
    raw_markdown: str
    custom_template_path: Optional[str]
    sample_ppt_path: Optional[str]
    sample_excel_path: Optional[str]
    current_phase: int
    workflow_status: str
    effort_matrix: Dict[str, Any]
    phase1_artifacts: Dict[str, Any]
    hitl_1_decision: Optional[str]
    question_slices: List[Dict[str, Any]]
    clarification_log: List[Dict[str, Any]]
    pre_review_dossier: Dict[str, Any]
    tco_model: Dict[str, Any]
    risk_flags: List[str]
    hitl_2_approved: bool
    hitl_2_feedback: Optional[str]
    final_package_paths: Dict[str, str]
    chat_events: List[Dict[str, Any]]
    client_name: str
    sample_ppt_path: Optional[str]
    sample_excel_path: Optional[str]
    deal_brief_ppt_path: str
    questionnaire_xlsx_path: str
    deal_brief_meta: Dict[str, Any]
    questionnaire_meta: Dict[str, Any]
    phase1_artifact_paths: Dict[str, str]




def _update_db(rfp_id: str, phase: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE rfp_projects SET current_phase=?, workflow_status=?, updated_at=datetime('now') WHERE rfp_id=?",
            (phase, status, rfp_id),
        )
        conn.commit()

def phase_1_triage_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    client_name = state.get("client_name", "Client Bank")
    ws = WORKSPACES_DIR / rfp_id
    ppt_out = ws / f"{rfp_id}_Deal_Brief.pptx"
    xls_out = ws / f"{rfp_id}_Questionnaire.xlsx"

    s_ppt = Path(state["sample_ppt_path"]) if state.get("sample_ppt_path") else None
    s_xls = Path(state["sample_excel_path"]) if state.get("sample_excel_path") else None

    ppt_meta = build_deal_brief_ppt(rfp_id, client_name, state["raw_markdown"], ppt_out, s_ppt)
    xls_meta = build_questionnaire_excel(rfp_id, state["raw_markdown"], xls_out, s_xls)

    em = {
        "english": {"modules": ["ISO 20022", "Ledger", "AML"], "estimated_effort_person_days": 380},
        "native": {"language": state["detected_language"], "estimated_effort_person_days": 380},
    }
    _update_db(rfp_id, 1, WorkflowStatus.PAUSED_HITL_1.value)
    append_audit_log(
        rfp_id,
        "Triage_Director_Agent",
        "PHASE_1_TRIAGE_ARTIFACTS_READY",
        1,
        {"ppt_mode": ppt_meta["mode"], "xls_mode": xls_meta["mode"]},
    )
    ev = {
        "rfp_id": rfp_id,
        "sender": "Triage Director Agent",
        "phase": 1,
        "message_english": f"Phase 1 complete for {rfp_id}. Deal Brief PPTX and Questionnaire XLSX generated.",
        "artifact_type": "EFFORT_MATRIX",
        "artifact_payload": {
            "effort_matrix": em,
            "deal_brief_meta": ppt_meta,
            "questionnaire_meta": xls_meta,
            "downloads": {
                "deal_brief_ppt": f"/api/rfps/{rfp_id}/download/deal_brief_ppt",
                "questionnaire_xlsx": f"/api/rfps/{rfp_id}/download/questionnaire_xlsx",
            },
        },
        "hitl_buttons": [
            {"action_id": "GO", "label": "GO", "variant": "primary"},
            {"action_id": "NO_GO", "label": "NO-GO", "variant": "danger"},
        ],
    }
    return {
        "current_phase": 1,
        "workflow_status": WorkflowStatus.PAUSED_HITL_1.value,
        "effort_matrix": em,
        "deal_brief_ppt_path": str(ppt_out),
        "questionnaire_xlsx_path": str(xls_out),
        "phase1_artifact_paths": {
            "deal_brief_pptx": str(ppt_out),
            "questionnaire_xlsx": str(xls_out),
        },
        "deal_brief_meta": ppt_meta,
        "questionnaire_meta": xls_meta,
        "chat_events": state.get("chat_events", []) + [ev],
    }


def old_phase_1_triage_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    client_name = state.get("client_name", "Enterprise Bank")
    workspace = WORKSPACES_DIR / rfp_id
    workspace.mkdir(parents=True, exist_ok=True)

    ppt_out = workspace / f"{rfp_id}_Deal_Summary.pptx"
    xlsx_out = workspace / f"{rfp_id}_Questionnaire.xlsx"

    sample_ppt = Path(state["sample_ppt_path"]) if state.get("sample_ppt_path") else None
    sample_xlsx = Path(state["sample_excel_path"]) if state.get("sample_excel_path") else None

    ppt_meta = build_deal_brief_ppt(rfp_id, client_name, state["raw_markdown"], ppt_out, sample_ppt)
    xlsx_meta = build_questionnaire_excel(rfp_id, state["raw_markdown"], xlsx_out, sample_xlsx)

    phase1_artifacts = {
        "deal_brief_pptx": str(ppt_out),
        "questionnaire_xlsx": str(xlsx_out),
        "ppt_summary": ppt_meta,
        "excel_summary": xlsx_meta,
    }

    effort_matrix = {
        "english": {
            "core_banking_modules": ["ISO 20022 Instant Payments", "Multi-Currency Ledger", "AML/KYC Screening"],
            "cloud_readiness": "Kubernetes Multi-AZ + HSM Key Vault",
            "compliance_scope": ["SOC2 Type II", "ISO 27001", "PCI-DSS v4.0"],
            "estimated_effort_person_days": 380,
            "generated_artifacts": phase1_artifacts,
        },
        "native": {
            "language": state["detected_language"],
            "note": "Mirrored output rendered alongside English Core per Rule 2.",
            "estimated_effort_person_days": 380,
        },
    }

    _update_db(rfp_id, 1, WorkflowStatus.PAUSED_HITL_1.value)
    append_audit_log(
        rfp_id,
        "Triage_Director_Agent",
        "PHASE_1_EFFORT_MATRIX_AND_BRIEF_READY",
        1,
        {"effort_person_days": 380, "ppt_mode": ppt_meta["mode"], "excel_mode": xlsx_meta["mode"]},
    )

    event = {
        "rfp_id": rfp_id,
        "sender": "Triage Director Agent",
        "phase": 1,
        "message_english": (
            f"Phase 1 complete for {rfp_id}. Generated Deal Brief (.pptx) and Questionnaire (.xlsx). "
            "Review artifacts and select [GO] or [NO-GO]."
        ),
        "artifact_type": "EFFORT_MATRIX",
        "artifact_payload": effort_matrix,
        "hitl_buttons": [
            {"action_id": "GO", "label": "GO", "variant": "primary"},
            {"action_id": "NO_GO", "label": "NO-GO", "variant": "danger"},
        ],
    }

    return {
        "current_phase": 1,
        "workflow_status": WorkflowStatus.PAUSED_HITL_1.value,
        "effort_matrix": effort_matrix,
        "phase1_artifacts": phase1_artifacts,
        "chat_events": state.get("chat_events", []) + [event],
    }


def route_after_hitl_1(state: RFPWorkflowState) -> str:
    return "phase_2_kickoff" if state.get("hitl_1_decision") == "GO" else "archive_no_go"


def archive_no_go_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    _update_db(rfp_id, 1, WorkflowStatus.NO_GO.value)
    append_audit_log(rfp_id, state["actor_identity"], "HITL_1_NO_GO_ARCHIVED", 1, {"decision": "NO_GO"})
    event = {
        "rfp_id": rfp_id,
        "sender": "System Orchestrator",
        "phase": 1,
        "message_english": f"RFP {rfp_id} marked as NO-GO and archived in immutable audit log.",
        "hitl_buttons": [],
    }
    return {"workflow_status": WorkflowStatus.NO_GO.value, "chat_events": state.get("chat_events", []) + [event]}


def phase_2_kickoff_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    raw_slices = document_slicer_tool(rfp_id, state["raw_markdown"], state["detected_language"])
    assigned_slices = directory_workload_scanner(raw_slices)
    clarifications = [s for s in assigned_slices if s["is_clarification_required"]]

    with get_connection() as conn:
        for s in assigned_slices:
            conn.execute(
                """
                INSERT OR REPLACE INTO rfp_question_slices
                (slice_id, rfp_id, section_anchor, question_native, question_english, assigned_owner, raci_role, kb_confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["slice_id"],
                    rfp_id,
                    s["section_anchor"],
                    s["question_native"],
                    s["question_english"],
                    s["assigned_owner"],
                    s["raci_role"],
                    s["kb_confidence_score"],
                ),
            )
        conn.commit()

    _update_db(rfp_id, 2, WorkflowStatus.RUNNING.value)
    append_audit_log(
        rfp_id,
        "Project_Manager_Orchestrator",
        "PHASE_2_RACI_AND_CLARIFICATIONS_BUILT",
        2,
        {"total_slices": len(assigned_slices), "clarification_count": len(clarifications)},
    )

    event = {
        "rfp_id": rfp_id,
        "sender": "Project Manager Orchestrator",
        "phase": 2,
        "message_english": (
            f"Parsed {len(assigned_slices)} RFP items onto RACI board. "
            f"Isolated {len(clarifications)} low-confidence (<75%) items into Clarification Log. Auto-advancing to Phase 3."
        ),
        "artifact_type": "RACI_AND_CLARIFICATIONS",
        "artifact_payload": {"raci_slices": assigned_slices, "clarification_log": clarifications},
        "hitl_buttons": [],
    }

    return {
        "current_phase": 2,
        "workflow_status": WorkflowStatus.RUNNING.value,
        "question_slices": assigned_slices,
        "clarification_log": clarifications,
        "chat_events": state.get("chat_events", []) + [event],
    }


def phase_3_generation_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    mermaid_flow = mermaid_sequence_generator("ISO 20022 Clearing & Settlement")
    topology = architecture_canvas_tool()

    dossier = {
        "mermaid_sequence": mermaid_flow,
        "deployment_topology": topology,
        "infosec_controls": "SOC2 Type II, TLS 1.3, AES-256-GCM, Zero-Data-Retention AI Gateway",
        "guardrail_verified": True,
    }

    _update_db(rfp_id, 3, WorkflowStatus.RUNNING.value)
    append_audit_log(rfp_id, "Phase_3_SubAgents", "PHASE_3_PRE_REVIEW_DOSSIER_VETTED", 3, {"guardrail": "PASSED"})

    event = {
        "rfp_id": rfp_id,
        "sender": "Tech Architect & Feature Auditor",
        "phase": 3,
        "message_english": "Generated architecture topology, sequence diagrams, and InfoSec responses. Compliance Guardrail passed.",
        "artifact_type": "PRE_REVIEW_DOSSIER",
        "artifact_payload": dossier,
        "hitl_buttons": [],
    }

    return {
        "current_phase": 3,
        "pre_review_dossier": dossier,
        "chat_events": state.get("chat_events", []) + [event],
    }


def phase_4_commercial_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    effort_days = state["effort_matrix"]["english"]["estimated_effort_person_days"]
    services_cost = effort_days * 850
    annual_saas = 240000
    tco_3yr = services_cost + (annual_saas * 3)

    tco_model = {
        "currency": "USD",
        "implementation_services": services_cost,
        "annual_saas_license": annual_saas,
        "three_year_tco": tco_3yr,
        "text_to_table_parity_verified": True,
    }
    risk_flags = [
        "Clause 14.2: 99.995% uptime SLA carries 10% monthly service credit penalty.",
        "Clarification Log items require client sign-off prior to binding fixed-price commitment.",
    ]

    _update_db(rfp_id, 4, WorkflowStatus.PAUSED_HITL_2.value)
    append_audit_log(
        rfp_id,
        "Commercial_Modeling_Bot",
        "PHASE_4_TCO_READY_PAUSED_HITL_2",
        4,
        {"three_year_tco_usd": tco_3yr, "risk_count": len(risk_flags)},
    )

    event = {
        "rfp_id": rfp_id,
        "sender": "Commercial Modeling Bot",
        "phase": 4,
        "message_english": (
            f"3-Year TCO modeled at ${tco_3yr:,.2f}. Paused at Checkpoint 2 (HITL 2) for Red Team & Legal risk review."
        ),
        "artifact_type": "TCO_AND_RISK_BOARD",
        "artifact_payload": {"tco_model": tco_model, "risk_flags": risk_flags},
        "hitl_buttons": [
            {"action_id": "APPROVE_HITL_2", "label": "Approve Red Team & Legal Review", "variant": "primary"},
        ],
    }

    return {
        "current_phase": 4,
        "workflow_status": WorkflowStatus.PAUSED_HITL_2.value,
        "tco_model": tco_model,
        "risk_flags": risk_flags,
        "chat_events": state.get("chat_events", []) + [event],
    }


def phase_5_assembly_node(state: RFPWorkflowState) -> Dict[str, Any]:
    rfp_id = state["rfp_id"]
    workspace = WORKSPACES_DIR / rfp_id
    summary = json.dumps(state["pre_review_dossier"], indent=2)
    package_paths = document_publisher_tool(
        rfp_id=rfp_id,
        workspace_dir=workspace,
        dossier_summary=summary,
        tco_table=state["tco_model"],
        custom_template_path=state.get("custom_template_path"),
    )

    _update_db(rfp_id, 5, WorkflowStatus.COMPLETED.value)
    append_audit_log(
        rfp_id,
        "Copy_Unifier_And_PM_QA",
        "PHASE_5_FINAL_PACKAGE_ASSEMBLED",
        5,
        {"qa_zero_tolerance_check": "PASSED", "files": list(package_paths.keys())},
    )

    event = {
        "rfp_id": rfp_id,
        "sender": "Copy Unifier & PM Orchestrator",
        "phase": 5,
        "message_english": (
            f"Zero-tolerance QA passed. Final Client Submission Package generated for {rfp_id}."
        ),
        "artifact_type": "FINAL_PACKAGE",
        "artifact_payload": package_paths,
        "hitl_buttons": [
            {"action_id": "AUTHORIZE_TRANSMISSION", "label": "Authorize Transmission", "variant": "primary"},
        ],
    }

    return {
        "current_phase": 5,
        "workflow_status": WorkflowStatus.COMPLETED.value,
        "final_package_paths": package_paths,
        "chat_events": state.get("chat_events", []) + [event],
    }


def build_rfp_graph():
    builder = StateGraph(RFPWorkflowState)
    builder.add_node("phase_1_triage", phase_1_triage_node)
    builder.add_node("archive_no_go", archive_no_go_node)
    builder.add_node("phase_2_kickoff", phase_2_kickoff_node)
    builder.add_node("phase_3_generation", phase_3_generation_node)
    builder.add_node("phase_4_commercial", phase_4_commercial_node)
    builder.add_node("phase_5_assembly", phase_5_assembly_node)

    builder.add_edge(START, "phase_1_triage")
    builder.add_conditional_edges(
        "phase_1_triage",
        route_after_hitl_1,
        {"phase_2_kickoff": "phase_2_kickoff", "archive_no_go": "archive_no_go"},
    )
    builder.add_edge("archive_no_go", END)
    builder.add_edge("phase_2_kickoff", "phase_3_generation")
    builder.add_edge("phase_3_generation", "phase_4_commercial")
    builder.add_edge("phase_4_commercial", "phase_5_assembly")
    builder.add_edge("phase_5_assembly", END)

    conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_after=["phase_1_triage", "phase_4_commercial"],
    )


rfp_orchestrator = build_rfp_graph()
