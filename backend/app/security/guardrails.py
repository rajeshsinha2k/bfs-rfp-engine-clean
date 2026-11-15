import re
from typing import Dict, List
from urllib.parse import urlparse

COMPETITOR_BLOCKLIST = (
    "temenos",
    "finacle",
    "flexcube",
    "mambu",
    "thought machine",
    "fiserv",
    "fis global",
)

ALLOWED_URLS = (
    "bis.org",
    "federalreserve.gov",
    "ecb.europa.eu",
    "bcb.gov.br",
    "bankofengland.co.uk",
    "docs.aws.amazon.com",
    "learn.microsoft.com",
    "cloud.google.com",
)

CODE_LEAK_PATTERNS = [
    re.compile(r"```(?:python|javascript|typescript|java|sql|bash|sh)", re.IGNORECASE),
    re.compile(r"\b(?:def |class |import |SELECT .* FROM |AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,})\b"),
]

URL_PATTERN = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)


def run_compliance_guardrail(draft_text: str) -> Dict[str, object]:
    """Phase 3 Compliance Guardrail Interceptor: Blocks code leaks, competitors, and unverified URLs."""
    violations: List[str] = []
    lowered = draft_text.lower()

    for comp in COMPETITOR_BLOCKLIST:
        if comp in lowered:
            violations.append(f"COMPETITOR_MENTION_BLOCKED: '{comp}'")

    for pattern in CODE_LEAK_PATTERNS:
        if pattern.search(draft_text):
            violations.append("SOURCE_CODE_OR_SECRET_LEAK_BLOCKED")
            break

    for url in URL_PATTERN.findall(draft_text):
        domain = urlparse(url).netloc.lower()
        if not any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_URLS):
            violations.append(f"UNVERIFIED_EXTERNAL_URL_BLOCKED: '{domain}'")

    return {
        "passed": len(violations) == 0,
        "violations": violations,
    }
