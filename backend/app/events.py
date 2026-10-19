from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SecurityEvent
from app.security_engine.pii_detector import redact_pii

router = APIRouter(
    prefix="/events",
    tags=["Security Events"]
)


def log_security_event(
    prompt: str,
    status: str,
    risk_score: int,
    risk_level: str,
    reasons: list,
    db: Session,
    ml_classification: dict | None = None,
):
    details = {
        "risk_level": risk_level,
        "reasons": reasons,
    }
    if ml_classification is not None:
        details["ml_classification"] = ml_classification

    event = SecurityEvent(
        event_type=risk_level,
        risk_score=risk_score,
        action=status,
        prompt=redact_pii(prompt[:200])["redacted_text"],
        details=details,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "id": event.id,
        "timestamp": event.created_at.isoformat()
        if event.created_at else datetime.now(timezone.utc).isoformat(),
        "prompt": event.prompt,
        "status": event.action,
        "risk_score": event.risk_score,
        "risk_level": risk_level,
        "reasons": reasons,
        "ml_classification": ml_classification,
    }


def get_security_events(db: Session):
    events = (
        db.query(SecurityEvent)
        .order_by(SecurityEvent.id.desc())
        .all()
    )

    results = []

    for event in events:
        details = event.details or {}

        results.append({
            "id": event.id,
            "timestamp": event.created_at.isoformat()
            if event.created_at else None,
            "prompt": event.prompt,
            "status": event.action,
            "risk_score": event.risk_score,
            "risk_level": details.get(
                "risk_level",
                event.event_type
            ),
            "reasons": details.get("reasons", []),
            "ml_classification": details.get("ml_classification"),
            "action_request": details.get("action_request"),
        })

    return results


@router.get("/")
def list_security_events(
    db: Session = Depends(get_db)
):
    events = get_security_events(db)

    return {
        "total": len(events),
        "events": events
    }
