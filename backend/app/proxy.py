"""OpenAI-compatible inline chat-completion gateway endpoint."""

import hmac
import json
import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.ai_provider import AGENTGUARD_API_KEY, GROQ_MODEL, generate_chat_completion
from app.database import get_db
from app.events import log_security_event
from app.policies import evaluate_policy, get_pii_action
from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.normalizer import normalize_text
from app.security_engine.pii_detector import detect_pii, redact_pii
from app.security_engine.risk_scorer import calculate_risk
from app.security_engine.sandbox import MAX_RECURSION_DEPTH, inspect_tool_calls
from app.gateway_config import get_gateway_config

router = APIRouter(prefix="/v1", tags=["OpenAI-compatible Gateway"])


class AgentGuardAPIError(Exception):
    def __init__(self, status_code: int, body: dict[str, Any]):
        self.status_code = status_code
        self.body = body


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Any = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1, max_length=32)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=4096)
    tools: list[dict[str, Any]] | None = Field(default=None, max_length=24)
    tool_choice: Any = None
    stream: bool = False
    agentguard_recursion_depth: int = Field(default=0, ge=0, le=1000)

    @model_validator(mode="after")
    def bound_total_payload(self):
        message_size = sum(len(json.dumps(message.model_dump(exclude_none=True), default=str)) for message in self.messages)
        schema_size = len(json.dumps(self.tools or [], default=str))
        if message_size + schema_size > 50000:
            raise ValueError("The complete chat request cannot exceed 50,000 characters.")
        return self


def _error(message: str, code: str, status: int = 400, guard: dict | None = None):
    detail: dict[str, Any] = {"error": {"message": message, "type": "agentguard_policy_error", "code": code}}
    if guard:
        detail["agentguard"] = guard
    raise AgentGuardAPIError(status, detail)


def _extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    # Inspect text-only payloads. Multimodal data fails closed until an image
    # inspection stage is configured, rather than silently bypassing controls.
    if isinstance(content, list):
        parts = []
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                raise ValueError("Only text chat content is currently supported by the inspection pipeline.")
            parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    raise ValueError("Message content must be text.")


def _tool_intents(calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    intents = []
    for call in calls or []:
        function = call.get("function") or {}
        name = function.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A tool call is missing its function name.")
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                raise ValueError(f"Tool arguments for {name} are not valid JSON.")
        if not isinstance(arguments, dict):
            raise ValueError(f"Tool arguments for {name} must be a JSON object.")
        intents.append({"name": name, "arguments": arguments})
    return intents


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
    x_agentguard_recursion_depth: int | None = Header(default=None),
    db: Session = Depends(get_db),
):
    started = time.perf_counter()
    if not AGENTGUARD_API_KEY:
        _error("The gateway API key is not configured on this service.", "gateway_not_configured", 503)
    supplied_key = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    if not supplied_key or not hmac.compare_digest(supplied_key, AGENTGUARD_API_KEY):
        _error("A valid AgentGuard bearer API key is required.", "invalid_api_key", 401)
    if request.stream:
        _error("Streaming is not enabled for this demo gateway.", "streaming_not_supported", 501)

    depth = request.agentguard_recursion_depth if x_agentguard_recursion_depth is None else x_agentguard_recursion_depth
    if depth < 0 or depth > 1000:
        _error("Invalid recursion depth.", "invalid_recursion_depth")

    try:
        messages = [message.model_dump(exclude_none=True) for message in request.messages]
        text_parts = [_extract_text(message.get("content")) for message in messages]
        normalized_parts = [normalize_text(part) for part in text_parts]
        joined_text = "\n".join(normalized_parts)
        detection = detect_prompt_injection(joined_text)
        config = get_gateway_config(db)
        pii = detect_pii(joined_text, config.get("dlp_detectors"))
        risk = calculate_risk(detection, pii)
        history_tool_calls = [
            intent
            for message in messages
            for intent in _tool_intents(message.get("tool_calls"))
        ]
        offered_tools = []
        for tool in request.tools or []:
            function = tool.get("function") or {}
            name = function.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError("Each tool declaration must include a function name.")
            offered_tools.append({"name": name, "arguments": {}})
        sandbox = inspect_tool_calls(
            history_tool_calls + offered_tools, depth, db
        )
        policy = evaluate_policy(detection, risk, db, text=joined_text)
        pii_action = get_pii_action(db) if pii["detected"] else "allow"
    except (ValueError, TypeError, KeyError) as exc:
        _error(str(exc), "invalid_request")
    except Exception:
        # Inspection failure is fail-closed; do not send uninspected content upstream.
        event = log_security_event(
            prompt="[inspection stage failed]", status="BLOCKED", risk_score=100,
            risk_level="CRITICAL", reasons=["Security inspection failed; request stopped"], db=db,
        )
        _error("Security inspection failed; the request was stopped.", "inspection_failed", 503, {"event_id": event["id"], "verdict": "block"})

    block_reasons = list(detection.get("reasons", [])) + list(policy.get("reasons", [])) + list(sandbox["reasons"])
    if pii["detected"] and pii_action == "block":
        block_reasons.append(f"Sensitive data policy blocked: {', '.join(pii['types'])}")
    stages = [
        {"name": "Normalization", "status": "complete", "detail": "Unicode and invisible characters normalized"},
        {"name": "Prompt injection", "status": "blocked" if detection["detected"] else "complete", "detail": "; ".join(detection.get("reasons", [])) or "No override pattern found"},
        {"name": "DLP inspection", "status": "redacted" if pii["detected"] and pii_action in {"redact", "flag"} else "blocked" if pii["detected"] and pii_action == "block" else "complete", "detail": ", ".join(pii["types"]) or "No sensitive values found"},
        {"name": "Agent sandbox", "status": "blocked" if not sandbox["safe"] else "complete", "detail": "; ".join(sandbox["reasons"]) or "Tool declarations and recursion checks passed"},
        {"name": "Policy verdict", "status": "blocked" if not policy["allowed"] else "flagged" if policy.get("flagged") else "allow", "detail": "; ".join(policy.get("reasons", [])) or "Request passed active policy"},
    ]
    if detection.get("detected") or not policy["allowed"] or not sandbox["safe"] or (pii["detected"] and pii_action == "block"):
        event = log_security_event(
            prompt=joined_text[:1000], status="BLOCKED", risk_score=max(risk["score"], 82),
            risk_level=risk["level"], reasons=block_reasons or ["Request denied by policy"], db=db,
            metadata={"pipeline": stages, "sandbox": sandbox},
        )
        _error(
            "AgentGuard blocked this request before it reached the model.",
            "request_blocked", 403,
            {"verdict": "block", "risk_score": risk["score"], "reasons": block_reasons, "event_id": event["id"]},
        )

    sanitized_messages = []
    for message, normalized in zip(messages, normalized_parts):
        sanitized = dict(message)
        if isinstance(sanitized.get("content"), (str, list)):
            if pii["detected"] and pii_action in {"redact", "flag"}:
                normalized = redact_pii(normalized, config.get("dlp_detectors"))["redacted_text"]
            sanitized["content"] = normalized
        sanitized_messages.append(sanitized)

    upstream = await generate_chat_completion(
        sanitized_messages,
        model=request.model or GROQ_MODEL,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        tools=request.tools,
        tool_choice=request.tool_choice,
    )
    if not upstream.get("success"):
        event = log_security_event(
            prompt=joined_text[:1000], status="AI_ERROR", risk_score=risk["score"],
            risk_level=risk["level"], reasons=["Upstream model provider request failed"], db=db,
            metadata={"pipeline": stages, "sandbox": sandbox},
        )
        _error(upstream.get("error", "Upstream model provider failed."), "upstream_error", 502, {"event_id": event["id"]})

    data = upstream["data"]
    try:
        choice = data["choices"][0]
        answer = choice["message"]
    except (KeyError, IndexError, TypeError):
        _error("Upstream model provider returned an invalid response.", "invalid_upstream_response", 502)

    output_text = answer.get("content") or ""
    output_injection = detect_prompt_injection(normalize_text(output_text)).get("detected", False)
    output_pii = detect_pii(normalize_text(output_text), config.get("dlp_detectors"))
    if output_pii["detected"] and not output_injection:
        answer["content"] = redact_pii(normalize_text(output_text), config.get("dlp_detectors"))["redacted_text"]

    try:
        returned_tool_calls = _tool_intents(answer.get("tool_calls"))
    except ValueError:
        event = log_security_event(
            prompt=joined_text[:1000], status="OUTPUT_BLOCKED", risk_score=90,
            risk_level="CRITICAL", reasons=["Model returned malformed tool-call arguments"], db=db,
            metadata={"pipeline": stages},
        )
        _error("AgentGuard withheld a malformed tool request returned by the model.", "invalid_tool_call", 403, {"event_id": event["id"]})
    output_sandbox = inspect_tool_calls(
        returned_tool_calls, depth + 1 if returned_tool_calls else depth, db
    )
    if not output_sandbox["safe"]:
        event = log_security_event(
            prompt=joined_text[:1000], status="OUTPUT_BLOCKED", risk_score=90,
            risk_level="CRITICAL", reasons=output_sandbox["reasons"], db=db,
            metadata={"pipeline": stages, "sandbox": output_sandbox},
        )
        _error("AgentGuard withheld an unsafe tool request returned by the model.", "tool_call_blocked", 403, {"event_id": event["id"], "reasons": output_sandbox["reasons"]})

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    if output_injection:
        answer["content"] = None
        answer.pop("tool_calls", None)
        choice["finish_reason"] = "content_filter"
    output_status = (
        "OUTPUT_BLOCKED" if output_injection else
        "FLAGGED" if policy.get("flagged") or (pii["detected"] and pii_action == "flag") else
        "OUTPUT_REDACTED" if output_pii["detected"] else
        "REDACTED" if pii["detected"] and pii_action == "redact" else
        "ALLOWED"
    )
    audit_reasons = []
    if output_injection:
        audit_reasons.append("Instruction override pattern in model output; response withheld")
    elif output_pii["detected"]:
        audit_reasons.append(f"Sensitive model output redacted: {', '.join(output_pii['types'])}")
    if pii["detected"] and pii_action in {"redact", "flag"}:
        audit_reasons.append(f"Sensitive request values redacted: {', '.join(pii['types'])}")
    if policy.get("flagged"):
        audit_reasons.extend(policy.get("reasons", []))
    event = log_security_event(
        prompt=joined_text[:1000], status=output_status, risk_score=risk["score"],
        risk_level=risk["level"], reasons=audit_reasons, db=db,
        metadata={
            "pipeline": stages,
            "sandbox": output_sandbox,
            "output_scan": {"injection": output_injection, "pii_types": output_pii["types"]},
            "latency_ms": elapsed_ms,
        },
    )
    data.setdefault("id", f"chatcmpl-{uuid.uuid4().hex}")
    data["agentguard"] = {
        "verdict": "block" if output_injection else "flag" if policy.get("flagged") or pii_action == "flag" else "redact" if pii["detected"] or output_pii["detected"] else "allow",
        "risk_score": risk["score"],
        "redacted_types": sorted(set(pii["types"] + output_pii["types"])),
        "tool_calls_checked": len(history_tool_calls) + len(offered_tools) + len(returned_tool_calls),
        "recursion_depth": depth,
        "max_recursion_depth": MAX_RECURSION_DEPTH,
        "latency_ms": elapsed_ms,
        "event_id": event["id"],
        "pipeline": stages,
    }
    return data

