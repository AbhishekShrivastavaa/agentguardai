from typing import Any

from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.pii_detector import detect_pii, redact_pii
from app.security_engine.risk_scorer import calculate_risk
from app.security_engine.normalizer import normalize_text


def scan_text(text: str, enabled_types: dict[str, bool] | None = None) -> dict[str, Any]:
    """Scan text for prompt injection, PII, and security risk."""

    normalized = normalize_text(text)
    injection = detect_prompt_injection(normalized)
    pii = detect_pii(normalized, enabled_types)
    risk = calculate_risk(injection, pii)

    return {
        "safe": not injection.get("detected", False),
        "injection": injection,
        "pii": pii,
        "risk": risk,
        "risk_score": risk.get("score", 0),
        "risk_level": risk.get("level", "LOW"),
        "normalized": normalized != text,
    }


def scan_and_redact(text: str, enabled_types: dict[str, bool] | None = None) -> dict[str, Any]:
    """Scan text and provide a redacted version."""

    result = scan_text(text, enabled_types)
    redaction = redact_pii(normalize_text(text), enabled_types)

    result["redacted_text"] = redaction["redacted_text"]
    result["pii_redacted"] = redaction["detected"]

    return result
