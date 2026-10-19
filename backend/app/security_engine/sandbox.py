"""Fail-closed checks for tool requests carried through the gateway."""

import ipaddress
import json
import re
import socket
from urllib.parse import unquote
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.models import InventoryItem
from app.gateway_config import get_gateway_config
from app.security_engine.injection_detector import detect_prompt_injection
from app.security_engine.normalizer import normalize_text
from app.security_engine.pii_detector import detect_pii


MAX_RECURSION_DEPTH = 5
DANGEROUS_COMMAND = re.compile(
    r"(?:\brm\s+-[a-z]*r[a-z]*f\b|\bmkfs(?:\.[a-z0-9]+)?\b|"
    r"\bdd\s+if=|\bshutdown\b|\breboot\b|\bchmod\s+[-+]?777\b|"
    r"\bcurl\b[^\n|]*\|\s*(?:ba)?sh\b|\biwr\b[^\n|]*\|\s*iex\b|"
    r"\b(?:sudo\s+)?(?:rm|del|format)\b)", re.I,
)
URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.I)


def _restricted_host(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return True
    if not host or host in {"localhost", "metadata.google.internal", "instance-data"}:
        return True
    if host.endswith((".internal", ".local", ".localhost")):
        return True
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        # Numeric-looking non-standard IPv4 forms are ambiguous; reject them.
        if re.fullmatch(r"[0-9.]+", host):
            return True
        try:
            addresses = {row[4][0] for row in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
        except OSError:
            return True
        return not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        )


def inspect_tool_calls(tool_calls: list[dict], recursion_depth: int, db: Session) -> dict:
    """Validate every requested tool before the caller can forward a request."""
    findings: list[str] = []
    if recursion_depth > MAX_RECURSION_DEPTH:
        findings.append(f"Tool recursion depth exceeds the limit of {MAX_RECURSION_DEPTH}")

    config = get_gateway_config(db)
    configured_allowlist = set(config.get("tool_allowlist", []))
    registered = {
        item.name: item
        for item in db.query(InventoryItem).filter(InventoryItem.category == "tools").all()
    }
    inspected = []
    for call in tool_calls:
        name = call["name"]
        arguments = call.get("arguments", {})
        serialized = json.dumps(arguments, ensure_ascii=False, default=str)
        inspected_text = normalize_text(unquote(serialized))
        item = registered.get(name)
        reasons = []

        if not item:
            reasons.append("Tool is not registered in the AgentGuard inventory")
        elif configured_allowlist:
            if name not in configured_allowlist:
                reasons.append("Tool is not enabled in the Policy Studio allow-list")
        elif (item.data or {}).get("state", "Review") != "Sanctioned":
            reasons.append("Tool is not sanctioned; reviewer approval is required")

        schema = ((item.data or {}).get("parameter_schema") or (item.data or {}).get("schema")) if item else None
        if isinstance(schema, dict):
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            missing = [key for key in required if key not in arguments]
            if missing:
                reasons.append(f"Required tool parameter is missing: {missing[0]}")
            if schema.get("additionalProperties") is False:
                unknown = set(arguments) - set(properties)
                if unknown:
                    reasons.append(f"Unexpected tool parameter: {sorted(unknown)[0]}")
            type_map = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}
            for key, definition in properties.items():
                if key not in arguments or not isinstance(definition, dict):
                    continue
                expected_type = type_map.get(definition.get("type"))
                if expected_type and not isinstance(arguments[key], expected_type):
                    reasons.append(f"Tool parameter has an invalid type: {key}")

        if DANGEROUS_COMMAND.search(inspected_text):
            reasons.append("Dangerous command pattern in tool arguments")
        sensitive = detect_pii(serialized, config.get("dlp_detectors"))
        if sensitive["detected"]:
            reasons.append(f"Sensitive values in tool arguments must be redacted: {', '.join(sensitive['types'])}")
        if any(_restricted_host(match.group(0).rstrip(".,);")) for match in URL_PATTERN.finditer(inspected_text)):
            reasons.append("Private or cloud-metadata network destination in tool arguments")
        if detect_prompt_injection(inspected_text).get("detected"):
            reasons.append("Prompt injection found in tool arguments")

        inspected.append({"name": name, "safe": not reasons, "reasons": reasons})
        findings.extend(f"{name}: {reason}" for reason in reasons)

    return {
        "safe": not findings,
        "max_recursion_depth": MAX_RECURSION_DEPTH,
        "requested_recursion_depth": recursion_depth,
        "tools": inspected,
        "reasons": findings,
    }

