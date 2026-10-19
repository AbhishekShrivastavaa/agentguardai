import re
from urllib.parse import unquote
from typing import Any


PATTERNS = {
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "PHONE": re.compile(
        r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?"
        r"(?:\d[-.\s]?){9,12}(?!\d)"
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
    "API_KEY": re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{12,}|"
        r"AIza[A-Za-z0-9_-]{20,}|"
        r"gh[pousr]_[A-Za-z0-9]{20,})\b"
    ),
    "GITHUB_TOKEN": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "SLACK_TOKEN": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "AWS_SECRET_KEY": re.compile(
        r"(?i)(?:aws[_-]?)?(?:secret[_-]?access[_-]?key|secret[_-]?key)"
        r"\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{32,})"
    ),
    "PRIVATE_KEY": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        r"[\s\S]{1,8000}?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ),
    "AWS_ACCESS_KEY": re.compile(
        r"\bAKIA[0-9A-Z]{16}\b"
    ),
    "JWT_TOKEN": re.compile(
        r"\beyJ[A-Za-z0-9_-]+\."
        r"eyJ[A-Za-z0-9_-]+\."
        r"[A-Za-z0-9_-]+\b"
    ),
    "AADHAAR_LIKE": re.compile(
        r"(?<!\d)[2-9]\d{3}\s?\d{4}\s?\d{4}(?!\d)"
    ),
    "CREDIT_CARD": re.compile(
        r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"
    ),
}


def detect_pii(text: str, enabled_types: dict[str, bool] | None = None) -> dict[str, Any]:
    """Detect common PII and secret patterns in text."""

    findings = []

    if not isinstance(text, str) or not text:
        return {
            "detected": False,
            "count": 0,
            "findings": [],
            "types": [],
        }

    for pii_type, pattern in PATTERNS.items():
        if enabled_types is not None and not enabled_types.get(pii_type, False):
            continue
        for match in pattern.finditer(text):
            value = match.group(0)

            # Avoid classifying ordinary numeric text as a card number.
            if pii_type == "CREDIT_CARD":
                digits = re.sub(r"\D", "", value)
                if not 13 <= len(digits) <= 19:
                    continue
                # Require a valid Luhn checksum to reduce false positives.
                total = 0
                parity = len(digits) % 2
                for index, char in enumerate(digits):
                    digit = int(char)
                    if index % 2 == parity:
                        digit *= 2
                        if digit > 9:
                            digit -= 9
                    total += digit
                if total % 10:
                    continue

            findings.append({
                "type": pii_type,
                "start": match.start(),
                "end": match.end(),
                # Never return matched secret material in scan results.
                "masked_value": "[REDACTED]",
            })

    # If percent-encoding hid sensitive material, redact the complete encoded
    # value rather than trying to translate decoded character offsets.
    decoded = unquote(text)
    if decoded != text:
        for pii_type, pattern in PATTERNS.items():
            if enabled_types is not None and not enabled_types.get(pii_type, False):
                continue
            if pattern.search(decoded):
                findings.append({
                    "type": pii_type,
                    "start": 0,
                    "end": len(text),
                    "masked_value": "[REDACTED]",
                })

    # Deduplicate identical spans.
    unique = {}
    for finding in findings:
        key = (finding["start"], finding["end"])
        if key not in unique:
            unique[key] = finding

    results = sorted(
        unique.values(),
        key=lambda item: item["start"],
    )

    return {
        "detected": bool(results),
        "count": len(results),
        "findings": results,
        "types": sorted({item["type"] for item in results}),
    }


def redact_pii(text: str, enabled_types: dict[str, bool] | None = None) -> dict[str, Any]:
    """Return text with detected sensitive values redacted."""

    result = detect_pii(text, enabled_types)
    redacted = text

    # Replace from right to left to preserve character offsets.
    for finding in sorted(
        result["findings"],
        key=lambda item: item["start"],
        reverse=True,
    ):
        start = finding["start"]
        end = finding["end"]
        redacted = redacted[:start] + "[REDACTED]" + redacted[end:]

    return {
        "redacted_text": redacted,
        "detected": result["detected"],
        "count": result["count"],
        "types": result["types"],
    }
