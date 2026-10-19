from fastapi import APIRouter, Depends, HTTPException
import json
from pydantic import BaseModel, Field, model_validator
from typing import Any, Literal
import time
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.events import log_security_event
from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.pii_detector import detect_pii, redact_pii
from app.security_engine.risk_scorer import calculate_risk
from app.security_engine.scanner import scan_text
from app.policies import evaluate_policy, get_pii_action
from app.ai_provider import generate_ai_response
from app.security_engine.normalizer import normalize_text
from app.security_engine.sandbox import inspect_tool_calls
from app.gateway_config import get_gateway_config

router = APIRouter(
    prefix="/gateway",
    tags=["Security Gateway"],
)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)


class ToolCallIntent(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    arguments: Any = Field(default_factory=dict)


class ScanRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10000)
    use_ai: bool = True
    conversation: list[ConversationMessage] = Field(default_factory=list, max_length=16)
    tool_calls: list[ToolCallIntent] = Field(default_factory=list, max_length=12)
    recursion_depth: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def bound_total_payload(self):
        size = len(self.prompt) + sum(len(item.content) for item in self.conversation)
        size += len(json.dumps([item.model_dump() for item in self.tool_calls], default=str))
        if size > 50000:
            raise ValueError("The complete scan payload cannot exceed 50,000 characters.")
        return self


@router.post("/scan")
async def scan_request(
    request: ScanRequest,
    _current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    original_prompt = request.prompt
    raw_messages = [
        {"role": item.role, "content": item.content}
        for item in request.conversation
    ]
    raw_context = "\n".join([item["content"] for item in raw_messages] + [original_prompt])
    normalized_messages = [
        {**item, "content": normalize_text(item["content"])} for item in raw_messages
    ]
    normalized_prompt = normalize_text(original_prompt)
    scan_context = "\n".join([item["content"] for item in normalized_messages] + [normalized_prompt])

    # Stages 1–3: normalization, injection inspection, then DLP inspection.
    detection = detect_prompt_injection(scan_context)
    gateway_config = get_gateway_config(db)
    pii = detect_pii(scan_context, gateway_config.get("dlp_detectors"))
    risk = calculate_risk(detection, pii)
    stages = [
        {"name": "Normalization", "status": "complete", "detail": "Unicode compatibility and invisible characters checked"},
        {"name": "Prompt injection", "status": "blocked" if detection.get("detected") else "complete", "detail": "; ".join(detection.get("reasons", [])) or "No override pattern found"},
        {"name": "DLP inspection", "status": "redacted" if pii["detected"] else "complete", "detail": ", ".join(pii["types"]) or "No sensitive values found"},
    ]
    ml_classification = {
        "label": detection.get("model_label", "benign"),
        "attack_probability": detection.get("model_probability", 0.5),
        "threshold": detection.get("model_threshold", 0.9),
        "available": detection.get("model_available", False),
    }

    # Stage 4: enforce the tool allow-list, parameter checks and recursion cap.
    sandbox = inspect_tool_calls(
        [call.model_dump() for call in request.tool_calls], request.recursion_depth, db
    )
    stages.append({
        "name": "Agent sandbox",
        "status": "blocked" if not sandbox["safe"] else "complete",
        "detail": "; ".join(sandbox["reasons"]) or (
            "No tool invocation supplied" if not request.tool_calls and request.recursion_depth == 0
            else "Tool policy passed"
        ),
    })

    # Stage 5: evaluate the active policy only after inspection is complete.
    policy = evaluate_policy(detection, risk, db=db, text=scan_context)
    stages.append({
        "name": "Policy verdict",
        "status": "blocked" if not policy["allowed"] or not sandbox["safe"] else "flagged" if policy.get("flagged") else "allow",
        "detail": "; ".join(policy.get("reasons", [])) or "Request passed active policy",
    })

    if not sandbox["safe"]:
        reasons = sandbox["reasons"]
        event = log_security_event(
            prompt=original_prompt,
            status="BLOCKED",
            risk_score=max(risk["score"], 90),
            risk_level="CRITICAL",
            reasons=reasons,
            db=db,
            ml_classification=ml_classification,
            metadata={"pipeline": stages, "sandbox": sandbox},
        )
        return {
            "status": "BLOCKED", "blocked": True, "risk_score": max(risk["score"], 90),
            "risk_level": "CRITICAL", "risk_threshold": policy["risk_threshold"],
            "detection_reasons": detection.get("reasons", []), "policy_reasons": reasons,
            "pii_detected": pii["detected"], "pii_types": pii["types"],
            "ml_classification": ml_classification, "event_id": event["id"],
            "ai_response": None, "pipeline": stages, "sandbox": sandbox,
            "verdict": "block",
        }

    # 3. Apply the configured PII policy
    pii_action = get_pii_action(db) if pii["detected"] else "allow"
    prompt = normalized_prompt
    prior_messages = normalized_messages
    prompt_redacted = False

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
            metadata={"pipeline": stages},
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
            "pipeline": stages,
            "verdict": "block",
        }

    if pii["detected"] and pii_action in {"redact", "flag"}:
        prompt_redacted = True
        prompt = redact_pii(prompt, gateway_config.get("dlp_detectors"))["redacted_text"]
        prior_messages = [
            {
                **item,
                "content": redact_pii(item["content"], gateway_config.get("dlp_detectors"))["redacted_text"],
            }
            for item in prior_messages
        ]

    pii_flagged = (pii["detected"] and pii_action == "flag") or policy.get("flagged", False)

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
            metadata={"pipeline": stages, "sandbox": sandbox},
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
            "pipeline": stages,
            "verdict": "block",
        }

    # 5. Scan-only mode
    if not request.use_ai:
        status = "FLAGGED" if pii_flagged else "REDACTED" if prompt_redacted else "ALLOWED"
        scan_reasons = []
        if pii["detected"]:
            suffix = " and flagged" if pii_action == "flag" else ""
            scan_reasons.append(f"Sensitive values redacted{suffix}: {', '.join(pii['types'])}")
        if policy.get("flagged"):
            scan_reasons.extend(policy.get("reasons", []))

        event = log_security_event(
            prompt=original_prompt,
            status=status,
            risk_score=risk["score"],
            risk_level=risk["level"],
            reasons=scan_reasons,
            db=db,
            ml_classification=ml_classification,
            metadata={"pipeline": stages, "sandbox": sandbox},
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
            "prompt_redacted": prompt_redacted,
            "event_id": event["id"],
            "ai_response": None,
            "pipeline": stages,
            "sandbox": sandbox,
            "verdict": "flag" if pii_flagged else "redact" if prompt_redacted else "allow",
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
            metadata={"pipeline": stages, "sandbox": sandbox},
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
    output_scan = scan_text(ai_response, gateway_config.get("dlp_detectors"))
    output_reasons = []
    output_injection = output_scan["injection"].get("detected", False)

    if output_injection:
        output_reasons.append("Instruction override pattern detected in model output; response withheld")
        ai_response = None

    output_pii = output_scan["pii"].get("detected")
    if output_pii:
        if not output_injection:
            ai_response = redact_pii(normalize_text(ai_result["response"]), gateway_config.get("dlp_detectors"))["redacted_text"]
        output_reasons.append("Sensitive values were redacted from the model response")

    # Prompt-like language in a normal answer is a signal for review. It is not
    # enough on its own to suppress every model response.
    output_blocked = output_injection

    # 8. Save the security event
    if output_injection:
        final_status = "OUTPUT_BLOCKED"
    elif output_pii:
        final_status = "OUTPUT_REDACTED"
    elif pii["detected"] and pii_action in {"redact", "flag"}:
        final_status = "REDACTED"
    elif pii_flagged:
        final_status = "FLAGGED"
    else:
        final_status = "ALLOWED"

    event_reasons = list(output_reasons)

    if pii_flagged:
        event_reasons.append(
            f"PII detected: {', '.join(pii['types'])}"
        )
    elif pii["detected"] and pii_action in {"redact", "flag"}:
        event_reasons.append(f"Sensitive values redacted: {', '.join(pii['types'])}")

    event = log_security_event(
        prompt=original_prompt,
        status=final_status,
        risk_score=risk["score"],
        risk_level=risk["level"],
        reasons=event_reasons,
        db=db,
        ml_classification=ml_classification,
        metadata={
            "pipeline": stages,
            "sandbox": sandbox,
            "output_scan": {
                "risk_score": output_scan["risk_score"],
                "pii_types": output_scan["pii"]["types"],
                "reasons": output_reasons,
            },
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
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
        "prompt_redacted": prompt_redacted,
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
        "pipeline": stages,
        "sandbox": sandbox,
        "verdict": "block" if output_injection else "flag" if pii_flagged else "redact" if (prompt_redacted or output_pii) else "allow",
    }
