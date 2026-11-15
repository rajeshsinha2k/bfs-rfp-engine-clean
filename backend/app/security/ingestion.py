from pathlib import Path
import pdfplumber
from docx import Document


def ingest_document_to_markdown(file_path: Path) -> str:
    """Rule 1 (Document Format Agnostic): Converts .pdf and .docx into structural Markdown preserving tables and headers."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(file_path)
    if suffix == ".docx":
        return _parse_docx(file_path)
    return file_path.read_text(encoding="utf-8", errors="ignore")


# Alias for backward/forward compatibility across routers and tests
parse_document_to_markdown = ingest_document_to_markdown


def _parse_pdf(file_path: Path) -> str:
    md_blocks: list[str] = [f"# Document: {file_path.name}"]
    with pdfplumber.open(str(file_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            md_blocks.append(f"\n## Page {page_num}")
            tables = page.extract_tables() or []
            for table in tables:
                md_blocks.append(_table_to_markdown(table))
            text = page.extract_text() or ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped:
                    md_blocks.append(stripped)
    return "\n".join(md_blocks)


def _parse_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    md_blocks: list[str] = [f"# Document: {file_path.name}"]
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = (para.style.name or "").lower()
        if "heading 1" in style_name:
            md_blocks.append(f"\n# {text}")
        elif "heading 2" in style_name:
            md_blocks.append(f"\n## {text}")
        elif "heading" in style_name:
            md_blocks.append(f"\n### {text}")
        else:
            md_blocks.append(text)
    for table in doc.tables:
        rows = [[cell.text.strip().replace("\n", " ") for cell in row.cells] for row in table.rows]
        md_blocks.append("\n" + _table_to_markdown(rows))
    return "\n".join(md_blocks)


def _table_to_markdown(rows: list[list[str | None]]) -> str:
    if not rows:
        return ""
    cleaned = [[(cell or "").strip().replace("|", "\\|") for cell in row] for row in rows]
    header = "| " + " | ".join(cleaned[0]) + " |"
    separator = "| " + " | ".join("---" for _ in cleaned[0]) + " |"
    body = ["| " + " | ".join(r) + " |" for r in cleaned[1:]]
    return "\n".join([header, separator] + body)
