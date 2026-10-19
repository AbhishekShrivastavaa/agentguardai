from typing import Any

from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.pii_detector import detect_pii, redact_pii
from app.security_engine.risk_scorer import calculate_risk


def scan_text(text: str) -> dict[str, Any]:
    """Scan text for prompt injection, PII, and security risk."""

    injection = detect_prompt_injection(text)
    pii = detect_pii(text)
    risk = calculate_risk(injection)

    return {
        "safe": not injection.get("detected", False),
        "injection": injection,
        "pii": pii,
        "risk": risk,
        "risk_score": risk.get("score", 0),
        "risk_level": risk.get("level", "LOW"),
    }


def scan_and_redact(text: str) -> dict[str, Any]:
    """Scan text and provide a redacted version."""

    result = scan_text(text)
    redaction = redact_pii(text)

    result["redacted_text"] = redaction["redacted_text"]
    result["pii_redacted"] = redaction["detected"]

    return result