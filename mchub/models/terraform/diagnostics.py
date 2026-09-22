"""Extract error diagnostics without interpreting provider-specific failures."""
import json
import re


def extract_diagnostics(log):
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    diagnostics = []
    plain = []
    for line in log.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            plain.append(line)
            continue
        if not isinstance(event, dict):
            continue
        diagnostic = event.get("diagnostic") or {}
        if diagnostic.get("severity") == "error":
            parts = ["Error: " + diagnostic.get("summary", "Terraform error"), diagnostic.get("detail")]
            if diagnostic.get("address"):
                parts.append("with " + diagnostic["address"])
            location = diagnostic.get("range") or {}
            if location.get("filename"):
                parts.append(f"on {location['filename']} line {location.get('start', {}).get('line', '?')}")
            parts.append((diagnostic.get("snippet") or {}).get("code"))
            diagnostics.append("\n".join(part for part in parts if part))
    # Human-readable Terraform diagnostics are boxed, or begin with Error:.
    block = []
    for line in plain:
        cleaned = re.sub(r"^\s*│ ?", "", line)
        if re.match(r"^\s*Error:", cleaned):
            if block:
                diagnostics.append("\n".join(block).strip())
            block = [cleaned]
        elif block:
            if line.strip() in ("╵", "╷"):
                diagnostics.append("\n".join(block).strip())
                block = []
            else:
                block.append(cleaned)
    if block:
        diagnostics.append("\n".join(block).strip())
    return "\n\n".join(diagnostics)


def is_timeout(diagnostic):
    return bool(re.search(
        r"\b(?:timed out|time out|deadline exceeded)\b|\btimeout\b(?=[ \t]*(?:[-:,;]|\.(?:\s|$)|$|while\b|waiting\b))",
        diagnostic, re.I | re.M,
    ))
