import re
import html
from urllib.parse import unquote
from app.security_engine.ml_classifier import classify_prompt
from app.security_engine.normalizer import normalize_text


PATTERNS = [
    (
        r"ignore\s+(all\s+)?previous\s+instructions",
        "Possible prompt injection"
    ),
    (
        r"\b(disregard|forget|override|ignore)\b[\s\S]{0,80}\b(system|developer|previous|prior|above)\b[\s\S]{0,60}\b(instructions?|rules?|prompt|message)\b",
        "Instruction hierarchy override attempt",
    ),
    (
        r"^\s*(?:(?:please|can\s+you|could\s+you|would\s+you)\s+){0,2}(?:show|reveal|print|repeat|quote|summarize)\s+(?:(?:me|us)\s+)?(?:(?:the|your|hidden|system|developer)\s+){0,3}(?:system\s+prompt|developer\s+instructions|hidden\s+instructions)",
        "System prompt extraction attempt"
    ),
    (
        r"^\s*(?:(?:please|can\s+you|could\s+you|would\s+you|will\s+you)\s+){0,2}(?:show|tell|give|send|print|display|reveal|list|share|expose)\s+(?:(?:me|us)\s+)?(?:(?:the|your|all|any|actual|hidden|configured|stored|private|server|provider)\s+){0,3}(?:api|access|secret|private|auth|bearer|service|provider)\s*[-_ ]?(?:keys?|tokens?|credentials?|secrets?)\b",
        "Possible credential disclosure request"
    ),
    (
        r"\b(developer|system)\s+message\b[\s\S]{0,80}\b(reveal|repeat|print|expose|dump|quote)\b|\b(reveal|repeat|print|expose|dump|quote)\b[\s\S]{0,80}\b(developer|system)\s+message\b",
        "System or developer instruction extraction attempt",
    ),
    (
        r"^\s*(?:(?:please|can\s+you|could\s+you|would\s+you)\s+){0,2}(?:what(?:\s+is|'s)|give\s+me|tell\s+me)\s+(?:(?:your|the|actual|hidden|configured|stored|private|server|provider)\s+){0,3}(?:api|access|secret|private|auth|bearer|service|provider)\s*[-_ ]?(?:keys?|tokens?|credentials?|secrets?)\b",
        "Possible credential disclosure request"
    ),
    (
        r"^\s*(?:(?:please|can\s+you|could\s+you|would\s+you|i\s+want\s+you\s+to)\s+){0,2}(?:dump|print|read|expose|exfiltrate|upload|send|cat|export)\b[\s\S]{0,60}(?:\.env\b|\benvironment\s+variables?\b|\bprocess\.env\b|\bsecrets?\s+file\b|\bcredentials?\s+file\b)",
        "Possible environment secret extraction"
    ),
    (
        r"^\s*(?:(?:please|can\s+you|could\s+you|tell\s+me\s+how\s+to|show\s+me\s+how\s+to)\s+){0,2}(?:bypass|evade|disable|remove)\s+(?:the\s+)?(?:safety|security)\s+(?:filters?|controls?|guardrails?)",
        "Possible safety bypass"
    ),
]


def detect_prompt_injection(prompt: str) -> dict:
    prompt = normalize_text(prompt)
    matches = []
    decoded = normalize_text(unquote(html.unescape(prompt)))
    candidates = [prompt] if decoded == prompt else [prompt, decoded]

    for pattern, reason in PATTERNS:
        if any(re.search(pattern, candidate, re.IGNORECASE) for candidate in candidates):
            matches.append(reason)

    model = classify_prompt(decoded if decoded != prompt else prompt)
    if model["label"] == "attack":
        matches.append("ML model detected a likely prompt attack")

    reasons = list(dict.fromkeys(matches))
    return {
        "detected": bool(reasons),
        "reasons": reasons,
        "model_label": model["label"],
        "model_probability": model["attack_probability"],
        "model_threshold": model["threshold"],
        "model_available": model["available"],
    }
