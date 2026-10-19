from typing import Optional
from app.security_engine.pii_detector import redact_pii

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SecurityPolicy


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

    stored = (
        db.query(SecurityPolicy)
        .filter(
            SecurityPolicy.name == "default",
            SecurityPolicy.enabled.is_(True),
        )
        .first()
    )

    if stored:
        settings["risk_threshold"] = stored.risk_threshold
        settings["default_action"] = stored.action

    return settings

def evaluate_policy(
    detection: dict,
    risk: dict,
    db: Optional[Session] = None,
) -> dict:
    settings = get_effective_policies(db)
    reasons = []

    if settings["block_prompt_injection"] and detection.get("detected", False):
        reasons.append("Prompt injection detected")

    threshold = settings["risk_threshold"]

    if settings["block_high_risk"] and risk.get("score", 0) >= threshold:
        reasons.append(
            f"Risk score meets or exceeds threshold ({threshold})"
        )

    return {
        "allowed": len(reasons) == 0,
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
def list_policies(db: Session = Depends(get_db)):
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
        return "block"

    return policy.action