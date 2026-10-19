def calculate_risk(detection: dict, pii: dict | None = None) -> dict:
    """Return a bounded, explainable score from injection and DLP signals."""
    score = 0

    if detection.get("detected"):
        # Rules are high-confidence; the learned model alone is supporting
        # evidence and should not turn benign prose into a high-risk verdict.
        rule_matches = [
            reason for reason in detection.get("reasons", [])
            if not reason.startswith("ML model")
        ]
        score = 82 if rule_matches else 58
        if rule_matches and detection.get("model_label") == "attack":
            score = min(95, score + 8)

    pii_types = set((pii or {}).get("types", []))
    if pii_types:
        score = max(score, 64 if pii_types & {
            "API_KEY", "AWS_ACCESS_KEY", "AWS_SECRET_KEY", "PRIVATE_KEY",
            "GITHUB_TOKEN", "SLACK_TOKEN", "JWT_TOKEN", "CREDIT_CARD",
        } else 38)
        score = min(69, score + max(0, len(pii_types) - 1) * 2)

    if score >= 70:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level
    }
