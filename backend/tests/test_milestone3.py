from pathlib import Path
import docx

from backend.app.security.guardrails import run_compliance_guardrail
from backend.app.security.ingestion import ingest_document_to_markdown
from backend.app.security.privacy_and_translation import (
    redact_banking_pii,
    restore_banking_pii,
    verify_numeric_parity,
)


def test_docx_layout_aware_table_extraction(tmp_path: Path):
    sample_docx = tmp_path / "sample_rfp.docx"
    doc = docx.Document()
    doc.add_heading("1. Payment Requirements", level=1)
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Requirement"
    table.cell(0, 1).text = "SLA"
    table.cell(1, 0).text = "ISO 20022 Clearing"
    table.cell(1, 1).text = "99.99%"
    doc.save(str(sample_docx))

    md = ingest_document_to_markdown(sample_docx)
    assert "# 1. Payment Requirements" in md
    assert "| ISO 20022 Clearing | 99.99% |" in md


def test_banking_pii_redaction_and_restoration():
    raw = "Wire settlement to IBAN DE00000000000000000000 via SWIFT DEUTDEFF and notify tester@example.test."
    redacted, vault = redact_banking_pii(raw)
    assert "DE00000000000000000000" not in redacted
    assert "DEUTDEFF" not in redacted
    assert "tester@example.test" not in redacted
    assert restore_banking_pii(redacted, vault) == raw


def test_numeric_parity_check():
    assert verify_numeric_parity("Total 3-Year TCO is 1043000 USD over 36 months.", "O TCO total de 3 anos e 1043000 USD em 36 meses.")
    assert not verify_numeric_parity("Total TCO is 1043000 USD.", "Total TCO is 999000 USD.")


def test_compliance_guardrail_interceptor():
    bad_draft = "Unlike Temenos, our python def pay(): runs via https://unverified-blog.example.com/hack"
    res_bad = run_compliance_guardrail(bad_draft)
    assert res_bad["passed"] is False
    assert len(res_bad["violations"]) == 3

    good_draft = "Our ISO 20022 engine aligns with https://www.bis.org/cpmi/ standards on AWS https://docs.aws.amazon.com/."
    res_good = run_compliance_guardrail(good_draft)
    assert res_good["passed"] is True
