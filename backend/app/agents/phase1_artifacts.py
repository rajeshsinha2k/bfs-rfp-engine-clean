import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from openpyxl import Workbook, load_workbook
from pptx import Presentation
from pptx.util import Pt


def _extract_requirement_sections(markdown_text: str) -> Dict[str, List[str]]:
    """Groups extracted Markdown lines under headings for flexible mapping."""
    sections: Dict[str, List[str]] = {}
    current_heading = "Executive Overview & Core Banking Scope"
    sections[current_heading] = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_heading = line.lstrip("#").strip()
            sections.setdefault(current_heading, [])
        else:
            clean_line = re.sub(r"^[-*•]\s+", "", line)
            sections[current_heading].append(clean_line)

    return {k: v for k, v in sections.items() if v} or {
        "Executive Overview": [markdown_text.strip() or "Core banking digital transformation requirements."]
    }


def _match_relevant_points(heading: str, subheadings: List[str], sections: Dict[str, List[str]]) -> List[str]:
    """Matches requirement items to static PPT headings/subheadings via keyword overlap."""
    keywords = {
        w.lower()
        for w in re.findall(r"[a-zA-Z0-9]{3,}", f"{heading} {' '.join(subheadings)}")
    }
    matched: List[str] = []
    for sec_title, items in sections.items():
        sec_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9]{3,}", sec_title)}
        if keywords & sec_words:
            matched.extend(items[:4])
        else:
            for item in items:
                item_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9]{3,}", item)}
                if keywords & item_words:
                    matched.append(item)

    if not matched:
        for items in sections.values():
            matched.extend(items[:3])
            if len(matched) >= 4:
                break
    return matched[:6]


def build_deal_brief_ppt(
    rfp_id: str,
    client_name: str,
    markdown_text: str,
    output_path: Path,
    sample_ppt_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Introspects an optional sample Deal Brief .pptx (preserving slides, static headings & subheadings)
    and populates relevant requirement portions. Falls back to corporate default if no sample is fed.
    """
    sections = _extract_requirement_sections(markdown_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if sample_ppt_path and sample_ppt_path.exists():
        prs = Presentation(str(sample_ppt_path))
        structure_log: List[Dict[str, Any]] = []

        for idx, slide in enumerate(prs.slides, start=1):
            heading_text = ""
            subheadings: List[str] = []
            body_shape = None

            if slide.shapes.title and slide.shapes.title.text.strip():
                heading_text = slide.shapes.title.text.strip()

            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                if slide.shapes.title and shape == slide.shapes.title:
                    continue
                lines = [p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()]
                if lines and not heading_text:
                    heading_text = lines[0]
                    subheadings.extend(lines[1:])
                elif lines:
                    subheadings.extend(lines)
                if body_shape is None:
                    body_shape = shape

            heading_text = heading_text or f"Slide {idx} Overview"
            relevant_points = _match_relevant_points(heading_text, subheadings, sections)

            if body_shape is not None:
                tf = body_shape.text_frame
                if subheadings:
                    p_hdr = tf.add_paragraph()
                    p_hdr.text = f"[{rfp_id} - {client_name} Extracted Scope]"
                    p_hdr.font.bold = True
                    p_hdr.font.size = Pt(12)
                for pt_text in relevant_points:
                    p = tf.add_paragraph()
                    p.text = f"• {pt_text}"
                    p.font.size = Pt(11)

            structure_log.append(
                {"slide": idx, "heading": heading_text, "subheadings": subheadings, "populated_items": len(relevant_points)}
            )

        prs.save(str(output_path))
        return {"mode": "SAMPLE_DRIVEN", "slides_processed": len(structure_log), "structure": structure_log}

    prs = Presentation()
    default_slides = [
        ("Deal Brief & Executive Summary", ["Client Profile", "Strategic Objectives", "RFP Scope"]),
        ("Functional & Core Banking Requirements", ["Payments & Clearing", "Digital Channels", "Core Ledger"]),
        ("Cloud, Architecture & InfoSec Posture", ["Deployment Model", "Regulatory & Compliance", "SLA Targets"]),
    ]
    structure_log = []
    for idx, (heading, subs) in enumerate(default_slides, start=1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"{heading} — {client_name} ({rfp_id})"
        tf = slide.placeholders[1].text_frame
        tf.clear()
        relevant = _match_relevant_points(heading, subs, sections)
        for sub in subs:
            p_sub = tf.add_paragraph()
            p_sub.text = sub
            p_sub.font.bold = True
            p_sub.font.size = Pt(14)
        for item in relevant:
            p_item = tf.add_paragraph()
            p_item.text = f"  • {item}"
            p_item.font.size = Pt(12)
        structure_log.append({"slide": idx, "heading": heading, "subheadings": subs, "populated_items": len(relevant)})

    prs.save(str(output_path))
    return {"mode": "DEFAULT_CORPORATE", "slides_processed": len(structure_log), "structure": structure_log}


def _extract_requirement_items(markdown_text: str) -> List[Dict[str, str]]:
    """Extracts individual requirement statements or questions with their section anchor."""
    items: List[Dict[str, str]] = []
    current_section = "General Requirements"
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_section = line.lstrip("#").strip()
        elif not line.startswith("|"):
            clean = re.sub(r"^(\d+[\.)]|Q\d+[:.]|[-*•])\s*", "", line).strip()
            if len(clean) >= 8:
                items.append({"section": current_section, "text": clean})

    if not items:
        items.append({"section": "General", "text": "Confirm core banking functional & security compliance."})
    return items


def _classify_domain(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("security", "soc2", "iso 27001", "encryption", "pci", "gdpr")):
        return "InfoSec & Compliance"
    if any(k in t for k in ("cloud", "kubernetes", "aws", "azure", "latency", "api", "uptime", "sla")):
        return "Cloud & Architecture"
    if any(k in t for k in ("iso 20022", "payment", "ledger", "core", "swift", "aml", "kyc")):
        return "Core Banking & Payments"
    return "General & Commercial"


def build_questionnaire_excel(
    rfp_id: str,
    markdown_text: str,
    output_path: Path,
    sample_excel_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Introspects an optional sample Questionnaire .xlsx (preserving sheet names, header columns,
    and static classification rows) and populates extracted requirement items across them.
    """
    req_items = _extract_requirement_items(markdown_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if sample_excel_path and sample_excel_path.exists():
        wb = load_workbook(str(sample_excel_path))
        ws = wb.active
        headers = [str(cell.value).strip() if cell.value is not None else "" for cell in ws[1]]

        static_rows: List[List[Any]] = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(v is not None and str(v).strip() != "" for v in row):
                static_rows.append(list(row))

        for idx, item in enumerate(req_items, start=1):
            row_values: List[Any] = []
            domain_label = _classify_domain(item["text"])
            for col_idx, col_name in enumerate(headers):
                c_low = col_name.lower()
                if any(k in c_low for k in ("id", "no", "#")):
                    row_values.append(f"REQ-{idx:03d}")
                elif any(k in c_low for k in ("class", "domain", "category", "type")):
                    if static_rows and col_idx < len(static_rows[0]) and static_rows[(idx - 1) % len(static_rows)][col_idx]:
                        row_values.append(static_rows[(idx - 1) % len(static_rows)][col_idx])
                    else:
                        row_values.append(domain_label)
                elif any(k in c_low for k in ("section", "heading", "module")):
                    row_values.append(item["section"])
                elif any(k in c_low for k in ("question", "requirement", "description", "item", "scope")):
                    row_values.append(item["text"])
                elif any(k in c_low for k in ("status", "clarif")):
                    row_values.append("Review Required" if "custom" in item["text"].lower() else "Standard")
                else:
                    row_values.append("")
            ws.append(row_values)

        wb.save(str(output_path))
        return {
            "mode": "SAMPLE_DRIVEN",
            "sheet_name": ws.title,
            "columns": headers,
            "static_rows_preserved": len(static_rows),
            "populated_rows": len(req_items),
        }

    wb = Workbook()
    ws = wb.active
    ws.title = "RFP_Questionnaire"
    default_headers = [
        "Item ID",
        "Section Heading",
        "Domain Classification",
        "Requirement / Question",
        "Clarification Flag",
        "Preliminary Effort (Days)",
    ]
    ws.append(default_headers)

    for idx, item in enumerate(req_items, start=1):
        domain = _classify_domain(item["text"])
        is_custom = "custom" in item["text"].lower() or "legacy" in item["text"].lower()
        ws.append([
            f"REQ-{idx:03d}",
            item["section"],
            domain,
            item["text"],
            "YES (<75% KB)" if is_custom else "NO",
            15 if is_custom else 5,
        ])

    wb.save(str(output_path))
    return {
        "mode": "DEFAULT_CORPORATE",
        "sheet_name": ws.title,
        "columns": default_headers,
        "static_rows_preserved": 0,
        "populated_rows": len(req_items),
    }
