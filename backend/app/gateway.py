from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy.orm import Session

from app.database import get_db
from app.events import log_security_event
from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.pii_detector import detect_pii, redact_pii
from app.security_engine.risk_scorer import calculate_risk
from app.security_engine.scanner import scan_text
from app.policies import evaluate_policy, get_pii_action
from app.ai_provider import generate_ai_response

router = APIRouter(
    prefix="/gateway",
    tags=["Security Gateway"],
)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)


class ScanRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)
    use_ai: bool = True
    conversation: list[ConversationMessage] = Field(default_factory=list, max_length=16)


@router.post("/scan")
async def scan_request(
    request: ScanRequest,
    db: Session = Depends(get_db),
):
    original_prompt = request.prompt
    prompt = original_prompt

    # Analyze the full chat context before forwarding it to the model.
    prior_messages = [
        {"role": item.role, "content": item.content}
        for item in request.conversation
    ]
    scan_context = "\n".join(
        [item["content"] for item in prior_messages] + [prompt]
    )

    # 1. Scan the incoming prompt and prior conversation context
    detection = detect_prompt_injection(scan_context)
    pii = detect_pii(scan_context)
    risk = calculate_risk(detection)
    ml_classification = {
        "label": detection.get("model_label", "benign"),
        "attack_probability": detection.get("model_probability", 0.5),
        "threshold": detection.get("model_threshold", 0.9),
        "available": detection.get("model_available", False),
    }

    # 2. Evaluate injection and risk policies
    policy = evaluate_policy(detection, risk, db=db)

    # 3. Apply the configured PII policy
    pii_action = get_pii_action(db) if pii["detected"] else "allow"

    if pii["detected"] and pii_action == "block":
        event = log_security_event(
            prompt=original_prompt,
            status="BLOCKED",
            risk_score=risk["score"],
            risk_level=risk["level"],
            reasons=[
                f"PII detected: {', '.join(pii['types'])}"
            ],
            db=db,
            ml_classification=ml_classification,
        )

        return {
            "status": "BLOCKED",
            "blocked": True,
            "reason": "Sensitive information detected.",
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "pii_detected": True,
            "pii_types": pii["types"],
            "ml_classification": ml_classification,
            "event_id": event["id"],
            "ai_response": None,
        }

    if pii["detected"] and pii_action == "redact":
        prompt = redact_pii(prompt)["redacted_text"]
        prior_messages = [
            {
                **item,
                "content": redact_pii(item["content"])["redacted_text"],
            }
            for item in prior_messages
        ]

    pii_flagged = pii["detected"] and pii_action == "flag"

    # 4. Block injection or requests violating risk policy
    if not policy["allowed"]:
        reasons = list(detection.get("reasons", []))
        reasons.extend(policy.get("reasons", []))

        event = log_security_event(
            prompt=original_prompt,
            status="BLOCKED",
            risk_score=risk["score"],
            risk_level=risk["level"],
            reasons=reasons,
            db=db,
            ml_classification=ml_classification,
        )

        return {
            "status": "BLOCKED",
            "blocked": True,
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "risk_threshold": policy["risk_threshold"],
            "detection_reasons": detection.get("reasons", []),
            "policy_reasons": policy.get("reasons", []),
            "pii_detected": pii["detected"],
            "pii_types": pii["types"],
            "ml_classification": ml_classification,
            "event_id": event["id"],
            "ai_response": None,
        }

    # 5. Scan-only mode
    if not request.use_ai:
        status = "FLAGGED" if pii_flagged else "ALLOWED"

        event = log_security_event(
            prompt=original_prompt,
            status=status,
            risk_score=risk["score"],
            risk_level=risk["level"],
            reasons=(
                [f"PII detected: {', '.join(pii['types'])}"]
                if pii_flagged else []
            ),
            db=db,
            ml_classification=ml_classification,
        )

        return {
            "status": status,
            "blocked": False,
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "risk_threshold": policy["risk_threshold"],
            "detection_reasons": detection.get("reasons", []),
            "policy_reasons": policy.get("reasons", []),
            "pii_detected": pii["detected"],
            "pii_types": pii["types"],
            "ml_classification": ml_classification,
            "prompt_redacted": prompt != original_prompt,
            "event_id": event["id"],
            "ai_response": None,
        }

    # 6. Send the permitted prompt to Groq
    ai_result = await generate_ai_response(
        prompt,
        conversation=prior_messages,
    )

    if not ai_result.get("success"):
        event = log_security_event(
            prompt=original_prompt,
            status="AI_ERROR",
            risk_score=risk["score"],
            risk_level=risk["level"],
            reasons=["AI provider request failed"],
            db=db,
            ml_classification=ml_classification,
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message": ai_result.get("error", "AI provider request failed."),
                "event_id": event["id"],
            },
        )

    # 7. Scan AI output before returning it
    ai_response = ai_result["response"]
    output_scan = scan_text(ai_response)
    output_reasons = []

    if output_scan["injection"].get("detected"):
        output_reasons.append(
            "Potential prompt injection detected in AI output"
        )

    if output_scan["pii"].get("detected"):
        output_reasons.append(
            "Potential sensitive information detected in AI output"
        )

    output_blocked = bool(output_reasons)

    if output_blocked:
        ai_response = None

    # 8. Save the security event
    if output_blocked:
        final_status = "OUTPUT_BLOCKED"
    elif pii_flagged:
        final_status = "FLAGGED"
    else:
        final_status = "ALLOWED"

    event_reasons = list(output_reasons)

    if pii_flagged:
        event_reasons.append(
            f"PII detected: {', '.join(pii['types'])}"
        )

    event = log_security_event(
        prompt=original_prompt,
        status=final_status,
        risk_score=risk["score"],
        risk_level=risk["level"],
        reasons=event_reasons,
        db=db,
        ml_classification=ml_classification,
    )

    # 9. Return the result
    return {
        "status": final_status,
        "blocked": output_blocked,
        "risk_score": risk["score"],
        "risk_level": risk["level"],
        "risk_threshold": policy["risk_threshold"],
        "detection_reasons": detection.get("reasons", []),
        "policy_reasons": policy.get("reasons", []),
        "pii_detected": pii["detected"],
        "pii_types": pii["types"],
        "ml_classification": ml_classification,
        "prompt_redacted": prompt != original_prompt,
        "ai_model": ai_result.get("model"),
        "ai_response": ai_response,
        "output_scan": {
            "risk_score": output_scan["risk_score"],
            "risk_level": output_scan["risk_level"],
            "pii_detected": output_scan["pii"]["detected"],
            "pii_types": output_scan["pii"]["types"],
            "reasons": output_reasons,
        },
        "event_id": event["id"],
    }
