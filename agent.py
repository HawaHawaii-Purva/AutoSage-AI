"""Agent orchestration: plan -> tool -> retrieve -> synthesize."""
from __future__ import annotations

import json
import re
from typing import Any

from llm import chat
from rag_engine import retrieve
from tools import (
    TOOLS,
    extract_obd_code,
    maintenance_check,
    obd_code_lookup,
    parts_action_plan,
    safety_check,
    vehicle_system_triage,
)

SYSTEM_PROMPT = """You are AutoSage, a vehicle troubleshooting assistant for two-wheelers and four-wheelers.
You explain likely causes and practical next checks; you never claim a remote diagnosis is certain.
Use the retrieved evidence and tool output. Prefer inspection/testing before part replacement.
For safety-critical symptoms, recommend safe stopping and professional inspection.
Never provide instructions that would require unsafe road testing or dismantling safety-critical systems.
"""

PLANNER_PROMPT = """Choose exactly ONE tool for this vehicle query, or choose none.
Tools:
- obd_code_lookup: when a P0xxx/P1xxx-style diagnostic code is present.
- safety_check: when the symptom may create immediate safety risk (brakes, steering, fuel leak, severe overheating, smoke, flashing check-engine plus rough running).
- vehicle_system_triage: when the user describes symptoms but no stronger specialized tool is needed.
- maintenance_check: when the main request is scheduled/preventive maintenance.
- parts_action_plan: when the user explicitly asks what component may need inspection/replacement.
Return JSON only: {"tool":"tool_name_or_none","reason":"one sentence"}
"""


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"tool": "none", "reason": "Planner output could not be parsed."}


def _fallback_tool(vehicle_type: str, query: str) -> str:
    if extract_obd_code(query):
        return "obd_code_lookup"
    safety = safety_check(query)
    if safety["level"] != "ROUTINE":
        return "safety_check"
    return "vehicle_system_triage"


def _run_selected_tool(tool_name: str, vehicle_type: str, query: str, issue: str) -> dict[str, Any]:
    if tool_name == "obd_code_lookup":
        code = extract_obd_code(query)
        return obd_code_lookup(code or "UNKNOWN")
    if tool_name == "safety_check":
        return safety_check(issue)
    if tool_name == "vehicle_system_triage":
        return vehicle_system_triage(issue)
    if tool_name == "maintenance_check":
        return maintenance_check(vehicle_type, issue)
    if tool_name == "parts_action_plan":
        triage = vehicle_system_triage(issue)
        system = triage["systems"][0] if triage["systems"] else "general"
        return parts_action_plan(system, issue)
    return {"tool": "none", "message": "No specialized tool was needed."}


def detect_language(query: str) -> str:
    """Lightweight detection for common Romanized Hindi/Hinglish markers.

    This only influences the preferred response language; it never blocks or
    translates user input.
    """
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", query.lower())
    tokens = set(text.split())
    phrases = [
        "start nahi", "nahi ho", "problem kya", "check karo",
        "brake lagane", "band ho", "aa raha", "aa rahi", "rahi hai",
        "raha hai", "hai kya", "batao", "bata do",
    ]
    token_markers = {
        "meri", "mujhe", "mera", "gaadi", "gadi", "scooty", "karu",
        "karo", "kyu", "kyun", "awaz", "awaaz", "chal", "chalu",
        "garam", "dikkat", "kaise", "kab", "bahut", "zyada", "kam",
        "mein", "pe", "wala", "nahi",
    }
    phrase_score = sum(1 for p in phrases if p in text)
    token_score = len(tokens & token_markers)
    return "hinglish" if phrase_score + token_score >= 2 else "english"


def analyze(vehicle_type: str, make: str, model: str, year: str, fuel: str, query: str, language_mode: str = "Auto") -> dict[str, Any]:
    vehicle = f"{year} {make} {model} ({fuel})".strip()
    detected_language = detect_language(query)
    if language_mode.lower() == "hinglish":
        response_language = "Hinglish (Roman Hindi + English, matching the user’s style)"
    elif language_mode.lower() == "hindi":
        response_language = "Hindi (Devanagari, with English technical terms where useful)"
    elif language_mode.lower() == "english":
        response_language = "English"
    else:
        response_language = "Hinglish (Roman Hindi + English)" if detected_language == "hinglish" else "English"
    planner_messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": f"Vehicle type: {vehicle_type}\nVehicle: {vehicle}\nProblem: {query}"},
    ]
    try:
        plan = _parse_json(chat(planner_messages, temperature=0.0))
    except Exception:
        plan = {"tool": "none", "reason": "LLM planner unavailable; deterministic fallback selected."}

    tool_name = str(plan.get("tool", "none"))
    if tool_name not in set(TOOLS) | {"none"}:
        tool_name = "none"
    if tool_name == "none":
        tool_name = _fallback_tool(vehicle_type, query)

    tool_result = _run_selected_tool(tool_name, vehicle_type, query, query)
    rag_query = f"Vehicle type={vehicle_type}; vehicle={vehicle}; symptom={query}; tool result={tool_result}"
    evidence = retrieve(rag_query, vehicle_type, n_results=5)

    evidence_text = "\n\n".join(
        f"SOURCE {i+1}: {d['metadata'].get('title','Untitled')} | {d['metadata'].get('source_name','Unknown')}\n{d['text']}"
        for i, d in enumerate(evidence)
    )

    final_prompt = f"""{SYSTEM_PROMPT}

Vehicle: {vehicle}
Vehicle type: {vehicle_type}
User problem: {query}
Preferred response language: {response_language}

Language behavior:
- Understand English, Hindi, Hinglish, and Romanized Hindi input.
- Preserve technical names such as OBD-II, P0420, ABS, brake pad, oxygen sensor, etc.
- In Hinglish, write naturally in Roman script; do not force Devanagari.
- Match the user’s language style instead of translating the query word-for-word.
- Never let language choice reduce safety clarity.

TOOL USED:
{json.dumps(tool_result, indent=2)}

RETRIEVED EVIDENCE:
{evidence_text}

Create a clear answer in Markdown using these headings exactly:
### Assessment
### Likely causes
### What to check now
### What may need service or replacement
### Attention level
### When to stop driving
### Sources

Rules:
- Distinguish likely causes from confirmed faults.
- Do not invent exact repair costs or mileage intervals.
- For a diagnostic code, explain that the code narrows a system and does not prove a specific part is bad.
- For critical/high safety findings from the tool, make the safety action prominent.
- Under Sources, list 2-4 retrieved sources as markdown links.
"""
    try:
        answer = chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": final_prompt},
        ], temperature=0.2)
    except Exception as exc:
        answer = _fallback_answer(vehicle, query, tool_result, evidence, response_language)
        answer += f"\n\n> LLM fallback used: `{type(exc).__name__}`."

    mechanic_recommended = str(tool_result.get("level", "")).upper() in {"HIGH", "CRITICAL"}

    return {
        "answer": answer,
        "detected_language": detected_language,
        "response_language": response_language,
        "vehicle": vehicle,
        "tool": tool_name,
        "tool_result": tool_result,
        "planner_reason": plan.get("reason", ""),
        "evidence": evidence,
        "mechanic_recommended": mechanic_recommended,
    }


def _fallback_answer(vehicle: str, query: str, tool_result: dict[str, Any], evidence: list[dict[str, Any]], response_language: str = "English") -> str:
    hinglish = response_language.lower().startswith("hinglish")
    if hinglish:
        lines = ["### Assessment", f"**{vehicle}** ke liye aapne jo symptom bataya hai: _{query}_"]
        if tool_result.get("meaning"):
            lines += [f"\n### Likely causes", f"**{tool_result.get('meaning')}** ka matlab generic diagnostic-code level par ye hai. Sirf code ke basis par kisi part ko failed confirm nahi karna chahiye."]
            lines += ["\n### What to check now"] + [f"- {x}" for x in tool_result.get("checks", [])]
            lines += [f"\n### What may need service or replacement\n- {tool_result.get('action','Pehle inspect aur test karein; replacement fault confirm hone ke baad hi karein.')}"]
        else:
            lines += ["\n### Likely causes", "Is symptom ke multiple possible causes ho sakte hain; ye troubleshooting guidance hai, confirmed diagnosis nahi."]
            lines += ["\n### What to check now", "- Symptom exactly kab hota hai note karein.", "- Warning lights, leaks aur visible damage ko safely observe karein; hot ya moving parts ko touch na karein."]
            lines += ["\n### What may need service or replacement\n- Part replace karne se pehle affected system ko diagnose karein."]
        lines += ["\n### Attention level", str(tool_result.get("level", "ROUTINE"))]
        lines += ["\n### When to stop driving", tool_result.get("action", "Agar braking, steering, overheating, fuel leakage ya smoke ki wajah se safety compromise ho, gaadi rok kar professional help lein.")]
    else:
        lines = ["### Assessment", f"For **{vehicle}**, the symptom is: _{query}_"]
        if tool_result.get("meaning"):
            lines += [f"\n### Likely causes", f"**{tool_result.get('meaning')}** is the generic interpretation of the diagnostic code. This does not prove a failed component."]
            lines += ["\n### What to check now"] + [f"- {x}" for x in tool_result.get("checks", [])]
            lines += [f"\n### What may need service or replacement\n- {tool_result.get('action','Inspect and test before replacement.')}"]
        else:
            lines += ["\n### Likely causes", "The symptom can have multiple causes; the retrieved evidence should be treated as troubleshooting guidance, not a remote diagnosis."]
            lines += ["\n### What to check now", "- Note exactly when the symptom occurs.", "- Check visible warning lights, leaks, and obvious damage without touching hot or moving parts."]
            lines += ["\n### What may need service or replacement\n- Diagnose the affected system before replacing components."]
        lines += ["\n### Attention level", str(tool_result.get("level", "ROUTINE"))]
        lines += ["\n### When to stop driving", tool_result.get("action", "Stop driving and seek professional help if vehicle control, braking, overheating, fuel leakage, or smoke becomes unsafe.")]
    lines += ["\n### Sources"] + [f"- [{d['metadata'].get('source_name','Source')}]({d['metadata'].get('source_url','#')})" for d in evidence[:3]]
    return "\n".join(lines)
