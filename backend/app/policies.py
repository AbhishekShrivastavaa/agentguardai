from typing import Optional
from app.security_engine.pii_detector import redact_pii

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import SecurityPolicy
from app.gateway_config import get_gateway_config
from app.security_engine.normalizer import normalize_text


policy_router = APIRouter(
    prefix="/policies",
    tags=["Security Policies"],
)


DEFAULT_POLICIES = {
    "block_prompt_injection": True,
    "block_high_risk": True,
    "risk_threshold": 70,
}


def get_effective_policies(db: Optional[Session] = None) -> dict:
    settings = DEFAULT_POLICIES.copy()
    settings["default_action"] = "block"

    if db is None:
        return settings

    config = get_gateway_config(db)
    settings.update({"risk_threshold": config["risk_threshold"], "custom_rules": config["custom_rules"]})

    stored = (
        db.query(SecurityPolicy)
        .filter(
            SecurityPolicy.name == "default",
            SecurityPolicy.enabled.is_(True),
        )
        .first()
    )

    if stored:
        settings["default_action"] = stored.action
    settings["enabled_policies"] = db.query(SecurityPolicy).filter(
        SecurityPolicy.enabled.is_(True),
        SecurityPolicy.name.notin_(["default", "pii"]),
    ).all()

    return settings

def evaluate_policy(
    detection: dict,
    risk: dict,
    db: Optional[Session] = None,
    text: str = "",
) -> dict:
    settings = get_effective_policies(db)
    reasons = []

    flagged = False
    if settings["block_prompt_injection"] and detection.get("detected", False):
        sensitive_extraction = any(
            term in reason.lower()
            for reason in detection.get("reasons", [])
            for term in ("credential disclosure", "secret extraction", "system prompt extraction")
        )
        if sensitive_extraction or settings["default_action"] == "block":
            reasons.append("Prompt injection detected")
        elif settings["default_action"] == "flag":
            flagged = True
            reasons.append("Prompt injection sent for review by the active policy")
        elif settings["default_action"] == "redact":
            # Natural-language instructions cannot be reliably sanitized.
            reasons.append("Prompt injection cannot be safely sanitized")

    threshold = settings["risk_threshold"]

    if settings["block_high_risk"] and risk.get("score", 0) >= threshold:
        if settings["default_action"] == "block":
            reasons.append(f"Risk score meets or exceeds threshold ({threshold})")
        elif settings["default_action"] == "flag":
            flagged = True
            reasons.append(f"Risk score sent for review at threshold ({threshold})")
        elif settings["default_action"] == "redact":
            reasons.append(f"High-risk content cannot be sanitized (threshold {threshold})")

    for policy in settings.get("enabled_policies", []):
        if risk.get("score", 0) < policy.risk_threshold:
            continue
        if policy.action == "block":
            reasons.append(f"Policy '{policy.name}' blocked this risk score")
        elif policy.action == "flag":
            flagged = True
            reasons.append(f"Policy '{policy.name}' flagged this risk score")
    normalized_text = normalize_text(text).casefold()
    for rule in settings.get("custom_rules", []):
        phrase = str(rule.get("phrase", "")).strip().casefold()
        if not rule.get("enabled", True) or not phrase or phrase not in normalized_text:
            continue
        if rule.get("action") == "block":
            reasons.append(f"Custom policy phrase matched: {phrase[:48]}")
        else:
            flagged = True
            reasons.append(f"Custom policy flagged request: {phrase[:48]}")

    return {
        "allowed": not any(
            reason.startswith(("Prompt injection", "Risk score", "High-risk", "Policy '", "Custom policy phrase"))
            and "flagged" not in reason.lower() and "sent for review" not in reason.lower()
            for reason in reasons
        ),
        "flagged": flagged,
        "reasons": reasons,
        "risk_threshold": threshold,
        "action": settings["default_action"],
    }

class PolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    enabled: bool = True
    action: str = Field(pattern="^(allow|block|flag|redact)$")
    risk_threshold: float = Field(default=70, ge=0, le=100)


class PolicyUpdate(BaseModel):
    enabled: bool
    action: str = Field(pattern="^(allow|block|flag|redact)$")
    risk_threshold: float = Field(ge=0, le=100)


@policy_router.get("/")
def list_policies(_current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    policies = db.query(SecurityPolicy).order_by(
        SecurityPolicy.id
    ).all()

    return {
        "total": len(policies),
        "policies": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "enabled": p.enabled,
                "action": p.action,
                "risk_threshold": p.risk_threshold,
            }
            for p in policies
        ],
    }


@policy_router.post("/", status_code=201)
def create_policy(
    request: PolicyCreate,
    _current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(SecurityPolicy).filter(
        SecurityPolicy.name == request.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A policy with this name already exists.",
        )

    policy = SecurityPolicy(
        name=request.name,
        description=request.description,
        enabled=request.enabled,
        action=request.action,
        risk_threshold=request.risk_threshold,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return {
        "message": "Policy created",
        "id": policy.id,
        "name": policy.name,
    }


@policy_router.put("/{policy_id}")
def update_policy(
    policy_id: int,
    request: PolicyUpdate,
    _current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    policy = db.query(SecurityPolicy).filter(
        SecurityPolicy.id == policy_id
    ).first()

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Policy not found",
        )

    policy.enabled = request.enabled
    policy.action = request.action
    policy.risk_threshold = request.risk_threshold

    db.commit()
    db.refresh(policy)

    return {
        "message": "Policy updated",
        "id": policy.id,
        "name": policy.name,
        "enabled": policy.enabled,
        "action": policy.action,
        "risk_threshold": policy.risk_threshold,
    }


@policy_router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    _current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    policy = db.query(SecurityPolicy).filter(
        SecurityPolicy.id == policy_id
    ).first()

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Policy not found",
        )

    db.delete(policy)
    db.commit()

    return {"message": "Policy deleted", "id": policy_id}
def get_pii_action(db: Session) -> str:
    """Return the configured action for detected PII."""
    policy = (
        db.query(SecurityPolicy)
        .filter(
            SecurityPolicy.name == "pii",
            SecurityPolicy.enabled.is_(True),
        )
        .first()
    )

    if policy is None:
        # DLP is useful when it can safely mask the value and preserve context.
        return "redact"

    return policy.action
