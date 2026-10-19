"""Pre-execution decisions for agent requested actions.

This API returns a security decision only. It never executes shell, file,
network, secret, or tool actions.
"""
import ipaddress
import re
import socket
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.events import log_security_event
from app.models import InventoryItem, SecurityEvent
from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.sandbox import DANGEROUS_COMMAND, MAX_RECURSION_DEPTH
from app.security_engine.normalizer import normalize_text
from app.security_engine.pii_detector import detect_pii, redact_pii
from app.gateway_config import get_gateway_config

router = APIRouter(prefix="/gateway/actions", tags=["Agent Action Gateway"])

ActionType = Literal["shell", "file_read", "file_write", "network", "secret_access", "tool"]


class ActionRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=160)
    action_type: ActionType
    target: str = Field(min_length=1, max_length=2000)
    justification: str = Field(default="", max_length=1000)
    recursion_depth: int = Field(default=0, ge=0, le=1000)


class ApprovalRequest(BaseModel):
    note: str = Field(default="", max_length=1000)


SAFE_SHELL = re.compile(r"^(pwd|ls|git\s+(status|diff|log)(?:\s+--(?:short|stat|oneline))?)$", re.I)
DANGEROUS_SHELL = re.compile(
    r"(\brm\s+-rf\b|\bdel\s+/[sqf]\b|\bformat\s+[a-z]:|\bmkfs\b|\bdd\s+if=|"
    r"\bshutdown\b|\breboot\b|curl\b[^\n|]*\|\s*(ba)?sh\b|\biwr\b[^\n|]*\|\s*iex\b|"
    r"\b(remove-item|rmdir)\b[^\n]*\b(recurse|/s)\b)", re.I
)
SECRET_PATH = re.compile(r"(^|[/\\])(\.env(?:\.[^/\\]*)?|\.ssh|\.aws|credentials?(?:\.[^/\\]*)?|id_rsa|secrets?)([/\\]|$)", re.I)


def _private_or_metadata_host(target: str) -> bool:
    parsed = urlparse(target if "://" in target else f"https://{target}")
    host = (parsed.hostname or "").lower().strip(".")
    if host in {"localhost", "metadata.google.internal", "instance-data"}:
        return True
    try:
        address = ipaddress.ip_address(host)
        return not address.is_global
    except ValueError:
        if re.fullmatch(r"[0-9.]+", host):
            return True
        if host.endswith((".internal", ".local", ".localhost")):
            return True
        # Resolve hostnames before approval so a public-looking alias cannot
        # hide a private or link-local destination. Actual executors must pin
        # the vetted address to prevent DNS rebinding.
        try:
            addresses = {row[4][0] for row in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
        except OSError:
            return True
        if not addresses:
            return True
        for value in addresses:
            try:
                if not ipaddress.ip_address(value).is_global:
                    return True
            except ValueError:
                return True
        return False


def _outside_workspace(target: str) -> bool:
    root = Path(__file__).resolve().parents[2]
    candidate = Path(target)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
        return False
    except ValueError:
        return True


def _decision(request: ActionRequest, db: Session) -> tuple[str, int, list[str]]:
    target = normalize_text(unquote(request.target.strip()))
    justification = normalize_text(unquote(request.justification))
    prompt_detection = detect_prompt_injection(f"{target}\n{justification}")
    if prompt_detection.get("detected"):
        return "BLOCKED", 96, ["Prompt injection or instruction override detected in action request"]

    sensitive = detect_pii(f"{target}\n{justification}", get_gateway_config(db).get("dlp_detectors"))
    if sensitive["detected"]:
        return "BLOCKED", 92, [f"Sensitive values in the action request must be redacted: {', '.join(sensitive['types'])}"]

    if request.recursion_depth > MAX_RECURSION_DEPTH:
        return "BLOCKED", 98, [f"Agent recursion depth exceeds the limit of {MAX_RECURSION_DEPTH}"]

    if request.action_type == "shell":
        if DANGEROUS_SHELL.search(target) or DANGEROUS_COMMAND.search(target):
            return "BLOCKED", 100, ["Destructive or remote execution command is prohibited"]
        if not SAFE_SHELL.fullmatch(target):
            return "APPROVAL_REQUIRED", 76, ["Shell commands require reviewer approval unless they match the read-only command set"]
        return "ACTION_ALLOWED", 12, ["Command matches the read-only shell command set"]

    if request.action_type in {"file_read", "file_write"}:
        if SECRET_PATH.search(target):
            return "BLOCKED", 98, ["Credential and secret paths are protected from direct agent access"]
        if _outside_workspace(target):
            return "BLOCKED", 94, ["File access outside the configured workspace is prohibited"]
        if request.action_type == "file_write":
            return "APPROVAL_REQUIRED", 72, ["File writes require approval before execution"]
        return "ACTION_ALLOWED", 14, ["File read passed the current path policy"]

    if request.action_type == "network":
        if _private_or_metadata_host(target):
            return "BLOCKED", 98, ["Private network and cloud metadata destinations are blocked"]
        return "APPROVAL_REQUIRED", 70, ["Outbound network requests require approval before execution"]

    if request.action_type == "secret_access":
        return "APPROVAL_REQUIRED", 88, ["Secret access is quarantined and requires explicit reviewer approval"]

    tool = db.query(InventoryItem).filter(
        InventoryItem.category == "tools",
        InventoryItem.name == target,
    ).first()
    if not tool:
        return "BLOCKED", 90, ["Tool is not registered in the AgentGuard inventory"]
    tool_data = tool.data or {}
    if tool_data.get("state", "Review") != "Sanctioned":
        return "APPROVAL_REQUIRED", 74, ["Tool is not sanctioned and requires reviewer approval"]
    if str(tool_data.get("risk", "")).lower() == "high":
        return "APPROVAL_REQUIRED", 78, ["High-risk tool use requires reviewer approval"]
    return "ACTION_ALLOWED", 12, ["Tool is registered and sanctioned"]


@router.post("/evaluate")
def evaluate_action(
    request: ActionRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agents = db.query(InventoryItem).filter(InventoryItem.category == "agents").all()
    agent = next(
        (
            item for item in agents
            if item.name == request.agent_id or str((item.data or {}).get("id", "")) == request.agent_id
        ),
        None,
    )
    if agent is None:
        decision, score, reasons = "BLOCKED", 95, ["Agent identity is not registered in the AgentGuard inventory"]
    else:
        decision, score, reasons = _decision(request, db)
        if decision == "ACTION_ALLOWED" and (agent.data or {}).get("status") != "Protected":
            decision, score = "APPROVAL_REQUIRED", max(score, 72)
            reasons = ["Agent identity is not marked protected; reviewer approval is required"] + reasons
    # Do not persist caller-provided credential assignments in audit records.
    safe_target = "[secret identifier withheld]" if request.action_type == "secret_access" else redact_pii(normalize_text(unquote(request.target)))["redacted_text"]
    safe_justification = redact_pii(normalize_text(unquote(request.justification)))["redacted_text"]
    safe_target = re.sub(r"(?i)(api[_-]?key|access[_-]?token|token|password|secret)\s*[:=]\s*[^\s&]+", r"\1=[REDACTED]", safe_target)
    safe_justification = re.sub(r"(?i)(api[_-]?key|access[_-]?token|token|password|secret)\s*[:=]\s*[^\s&]+", r"\1=[REDACTED]", safe_justification)
    audit_summary = f"{request.action_type} request for agent {request.agent_id}: {safe_target}"
    event = log_security_event(
        prompt=audit_summary[:200],
        status=decision,
        risk_score=score,
        risk_level="HIGH" if score >= 70 else "LOW",
        reasons=reasons,
        db=db,
    )
    record = db.query(SecurityEvent).filter(SecurityEvent.id == event["id"]).first()
    record.details = {
        **(record.details or {}),
        "action_request": {
            "agent_id": request.agent_id,
            "action_type": request.action_type,
            "target": safe_target[:2000],
            "justification": safe_justification[:1000],
            "decision": decision,
            "approval_status": "pending" if decision == "APPROVAL_REQUIRED" else None,
        },
    }
    db.commit()
    return {
        "decision": decision,
        "allowed": decision == "ACTION_ALLOWED",
        "executed": False,
        "event_id": event["id"],
        "risk_score": score,
        "reasons": reasons,
        "approval_required": decision == "APPROVAL_REQUIRED",
        "message": "Policy decision only. AgentGuard does not execute the requested action.",
    }


@router.post("/{event_id}/approve")
def approve_action(
    event_id: int,
    request: ApprovalRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _review_action(event_id, request, "APPROVED", current_user, db)


@router.post("/{event_id}/reject")
def reject_action(
    event_id: int,
    request: ApprovalRequest,
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _review_action(event_id, request, "REJECTED", current_user, db)


def _review_action(event_id: int, request: ApprovalRequest, decision: str, reviewer: str, db: Session):
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    if event is None or event.action != "APPROVAL_REQUIRED":
        raise HTTPException(status_code=404, detail="Pending action approval not found")
    details = dict(event.details or {})
    action_request = dict(details.get("action_request") or {})
    action_request["approval_status"] = decision.lower()
    action_request["reviewer"] = reviewer
    action_request["review_note"] = redact_pii(normalize_text(request.note))["redacted_text"]
    details["action_request"] = action_request
    details["reasons"] = list(details.get("reasons", [])) + [f"Request {decision.lower()} by {reviewer}"]
    event.details = details
    event.action = decision
    db.commit()
    return {
        "decision": decision,
        "executed": False,
        "event_id": event.id,
        "message": f"Request {decision.lower()}; no action was executed.",
    }
