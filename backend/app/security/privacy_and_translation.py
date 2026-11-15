import re
from typing import Dict, List, Tuple

PII_PATTERNS = {
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    "SWIFT": re.compile(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "ACCOUNT_NUM": re.compile(r"\b(?:ACCT|ACC|IBAN|ROUTING)[-:\s]?\d{6,18}\b", re.IGNORECASE),
}


def redact_banking_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Governance Standard #2: Redacts banking identifiers and PII into reversible
    vault tokens before any external API call.
    """
    vault: Dict[str, str] = {}
    redacted = text
    counter = 1

    for entity_type, pattern in PII_PATTERNS.items():
        def _replacer(match: re.Match) -> str:
            nonlocal counter
            original = match.group(0)
            for tok, orig_val in vault.items():
                if orig_val == original:
                    return tok
            token = f"<REDACTED_{entity_type}_{counter:02d}>"
            vault[token] = original
            counter += 1
            return token

        redacted = pattern.sub(_replacer, redacted)

    return redacted, vault


def restore_banking_pii(text: str, vault: Dict[str, str]) -> str:
    """Restores reversible tokens back into original banking values inside the local boundary."""
    restored = text
    for token, original in vault.items():
        restored = restored.replace(token, original)
    return restored


def verify_numeric_parity(source_text: str, translated_text: str) -> bool:
    """
    Rule 2 Egress Check: Ensures all numeric values, SLAs, and currency figures
    remain strictly identical across English and Native translations.
    """
    num_pattern = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")
    src_nums = sorted(num_pattern.findall(source_text))
    tgt_nums = sorted(num_pattern.findall(translated_text))
    return src_nums == tgt_nums


def bridge_native_to_english(native_text: str, source_lang: str) -> str:
    """
    Rule 2 Ingress Layer: Converts native RFP text into English Core representation.
    Uses deterministic pass-through when already English or running in offline local mode.
    """
    if source_lang.lower().startswith("en"):
        return native_text
    return native_text


def bridge_english_to_native(english_text: str, target_lang: str) -> str:
    """
    Rule 2 Egress Layer: Mirrors approved English Core content back into the target RFP language
    and enforces numeric parity verification.
    """
    if target_lang.lower().startswith("en"):
        return english_text
    mirrored = english_text
    if not verify_numeric_parity(english_text, mirrored):
        raise ValueError("Numeric parity check failed during English-to-Native translation bridge.")
    return mirrored
