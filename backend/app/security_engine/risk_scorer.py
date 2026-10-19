def calculate_risk(detection: dict) -> dict:
    score = 0

    if detection["detected"]:
        score = 70

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