"""
shared/openspace_wrapper.py
Wrapper around OpenSpace skill engine. Invokes a skill and parses all
output markers: TG_DIGEST, TG_BLOCKED, TG_DISCOVERY, META_PROPOSAL,
EVOLVE_PROPOSAL, HIRE, JUDGE_RESULT, NEW_SKILL.
"""
import logging
import os
import re
from typing import Optional

log = logging.getLogger("openspace_wrapper")

OPENSPACE_MODEL = os.environ.get("OPENSPACE_MODEL", "openai/gpt-4o-mini")

# ── Marker definitions ────────────────────────────────────────────────────────
# Each entry: (marker_name, open_tag, close_tag)
# Some markers have attributes in the open tag (e.g. EVOLVE_PROPOSAL agent_id=X)
MARKERS = [
    ("TG_DIGEST",      "<<<TG_DIGEST>>>",            "<<<END_TG_DIGEST>>>"),
    ("TG_BLOCKED",     "<<<TG_BLOCKED>>>",            "<<<END_TG_BLOCKED>>>"),
    ("TG_DISCOVERY",   "<<<TG_DISCOVERY>>>",          "<<<END_TG_DISCOVERY>>>"),
    ("META_PROPOSAL",  "<<<META_PROPOSAL>>>",         "<<<END_META_PROPOSAL>>>"),
    ("JUDGE_RESULT",   "<<<JUDGE_RESULT>>>",          "<<<END_JUDGE_RESULT>>>"),
    ("NEW_SKILL",      None,                          "<<<END_NEW_SKILL>>>"),   # has attrs
    ("EVOLVE_PROPOSAL", None,                         "<<<END_EVOLVE_PROPOSAL>>>"),  # has attrs
    ("HIRE",           None,                          "<<<END_HIRE>>>"),         # has attrs
    # Worker output
    ("OUTPUT_JSON",    "<<<OUTPUT_JSON>>>",           "<<<END_OUTPUT_JSON>>>"),
    ("SPAWN",          "<<<SPAWN>>>",                 "<<<END_SPAWN>>>"),
    ("KILL",           "<<<KILL>>>",                  "<<<END_KILL>>>"),
    ("TASK",           "<<<TASK>>>",                  "<<<END_TASK>>>"),
]

_ATTR_PATTERNS = {
    "NEW_SKILL":       re.compile(r'<<<NEW_SKILL\b[^>]*>>>'),
    "EVOLVE_PROPOSAL": re.compile(r'<<<EVOLVE_PROPOSAL\b[^>]*>>>'),
    "HIRE":            re.compile(r'<<<HIRE\b[^>]*>>>'),
}


def extract_markers(text: str) -> dict:
    """
    Parse all output markers from LLM response text.
    Returns dict: {marker_name: [content_str, ...]}
    """
    results: dict = {}

    for name, open_tag, close_tag in MARKERS:
        found_list = []

        if open_tag is not None:
            # Simple fixed open tag
            parts = text.split(open_tag)
            for part in parts[1:]:
                if close_tag in part:
                    content = part.split(close_tag, 1)[0].strip()
                    if content:
                        found_list.append(content)
        else:
            # Attribute-bearing open tag — use regex
            pattern = _ATTR_PATTERNS.get(name)
            if pattern:
                for m in pattern.finditer(text):
                    start_idx = m.end()
                    remainder = text[start_idx:]
                    if close_tag in remainder:
                        content = remainder.split(close_tag, 1)[0].strip()
                        attrs_str = m.group(0)
                        if content:
                            found_list.append({"attrs": attrs_str, "content": content})

        if found_list:
            results[name] = found_list

    return results


async def run_skill(
    prompt: str,
    skill_content: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """
    Invoke OpenSpace with a prompt (optionally prepended with skill content).
    Returns {response: str, markers: dict, error: str|None}
    """
    from openspace import OpenSpace, OpenSpaceConfig
    import json

    effective_model = model or OPENSPACE_MODEL
    cfg = OpenSpaceConfig(llm_model=effective_model)

    full_prompt = prompt
    if skill_content:
        full_prompt = f"{skill_content}\n\n---\n\n{prompt}"

    try:
        async with OpenSpace(config=cfg) as cs:
            result = await cs.execute(full_prompt)
        response = result.get("response") or result.get("output") or ""
        markers = extract_markers(response)
        return {"response": response, "markers": markers, "error": None}
    except Exception as e:
        log.exception("openspace_run_failed")
        return {"response": "", "markers": {}, "error": str(e)}
