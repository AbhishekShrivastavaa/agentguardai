"""Administrator-managed controls for the demo gateway policy studio."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import GatewayConfiguration

router = APIRouter(prefix="/gateway/policy-config", tags=["Policy Studio"])

DEFAULT_GATEWAY_CONFIG = {
    "strictness": "balanced",
    "risk_threshold": 70,
    "dlp_detectors": {
        "EMAIL": True,
        "PHONE": True,
        "IP_ADDRESS": False,
        "API_KEY": True,
        "GITHUB_TOKEN": True,
        "SLACK_TOKEN": True,
        "AWS_ACCESS_KEY": True,
        "AWS_SECRET_KEY": True,
        "PRIVATE_KEY": True,
        "JWT_TOKEN": True,
        "AADHAAR_LIKE": True,
        "CREDIT_CARD": True,
    },
    "tool_allowlist": [],
    "custom_rules": [],
}


def get_gateway_config(db: Session) -> dict:
    stored = db.query(GatewayConfiguration).filter(
        GatewayConfiguration.key == "active"
    ).first()
    config = {**DEFAULT_GATEWAY_CONFIG, **(stored.value if stored else {})}
    config["dlp_detectors"] = {
        **DEFAULT_GATEWAY_CONFIG["dlp_detectors"],
        **config.get("dlp_detectors", {}),
    }
    config["custom_rules"] = config.get("custom_rules", [])
    config["tool_allowlist"] = config.get("tool_allowlist", [])
    return config


class CustomRule(BaseModel):
    phrase: str = Field(min_length=2, max_length=160)
    action: Literal["block", "flag"] = "block"
    enabled: bool = True


class GatewayConfigUpdate(BaseModel):
    strictness: Literal["balanced", "strict", "demo"] = "balanced"
    risk_threshold: int = Field(default=70, ge=0, le=100)
    dlp_detectors: dict[str, bool]
    tool_allowlist: list[str] = Field(default_factory=list, max_length=100)
    custom_rules: list[CustomRule] = Field(default_factory=list, max_length=20)


@router.get("")
def read_configuration(
    _user: str = Depends(get_current_user), db: Session = Depends(get_db),
):
    return get_gateway_config(db)


@router.put("")
def update_configuration(
    request: GatewayConfigUpdate,
    _user: str = Depends(get_current_user), db: Session = Depends(get_db),
):
    unknown = set(request.dlp_detectors) - set(DEFAULT_GATEWAY_CONFIG["dlp_detectors"])
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown DLP detector: {sorted(unknown)[0]}")
    allowlist = [name.strip() for name in request.tool_allowlist]
    if any(not name or len(name) > 160 for name in allowlist):
        raise HTTPException(status_code=422, detail="Tool names must contain 1 to 160 characters.")
    config = request.model_dump()
    config["tool_allowlist"] = sorted(set(allowlist))
    config["custom_rules"] = [rule.model_dump() for rule in request.custom_rules]
    record = db.query(GatewayConfiguration).filter(
        GatewayConfiguration.key == "active"
    ).first()
    if record is None:
        record = GatewayConfiguration(key="active", value=config)
        db.add(record)
    else:
        record.value = config
    db.commit()
    return get_gateway_config(db)

