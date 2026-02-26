"""Build exportable assessment summaries for Results page downloads."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from typing import Any


def _compact_text(value: str) -> str:
    """Normalize markdown/html-ish text into compact plain text."""
    if not value:
        return ""
    no_html = re.sub(r"<[^>]+>", " ", value)
    unescaped = html.unescape(no_html)
    return re.sub(r"\s+", " ", unescaped).strip()


def _first_sentence(value: str) -> str:
    """Extract first sentence from a text block."""
    text = _compact_text(value)
    if not text:
        return ""
    match = re.search(r"(?<=[.!?])\s+", text)
    if not match:
        return text
    return text[: match.start()].strip()


def _normalize_category(value: str, suffix: str) -> str:
    """Drop internal prefixes from category labels."""
    if not value:
        return "Other"
    normalized = value.replace(suffix, "").replace("Control", "").strip()
    return normalized or "Other"


def _load_frameworks(loader: Any) -> dict[str, dict[str, Any]]:
    """Load framework metadata keyed by framework id."""
    try:
        data = loader.load_yaml("frameworks.yaml")
    except Exception:
        return {}
    frameworks = data.get("frameworks", [])
    return {f.get("id"): f for f in frameworks if f.get("id")}


def _collect_framework_hits(
    risks: list[dict[str, Any]],
    controls: list[dict[str, Any]],
) -> dict[str, dict[str, set[str]]]:
    """Collect framework mapping IDs across selected risks and controls."""
    hits: dict[str, dict[str, set[str]]] = {}

    for risk in risks:
        mappings = risk.get("mappings", {}) or {}
        for framework_id, mapping_ids in mappings.items():
            if not mapping_ids:
                continue
            entry = hits.setdefault(framework_id, {"mappedItems": set(), "sources": set()})
            entry["mappedItems"].update(str(mid) for mid in mapping_ids if mid)
            entry["sources"].add("risks")

    for control in controls:
        mappings = control.get("mappings", {}) or {}
        for framework_id, mapping_ids in mappings.items():
            if not mapping_ids:
                continue
            entry = hits.setdefault(framework_id, {"mappedItems": set(), "sources": set()})
            entry["mappedItems"].update(str(mid) for mid in mapping_ids if mid)
            entry["sources"].add("controls")

    return hits


def build_assessment_export_summary(
    loader: Any,
    vayu: dict[str, Any],
    relevant_risks: list[str],
    controls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a portable summary with risks, controls, practices, and tools."""
    risk_entries: list[dict[str, Any]] = []
    risk_objects: list[dict[str, Any]] = []

    for risk_id in sorted(set(relevant_risks)):
        risk = loader.get_risk_details(risk_id) or {"id": risk_id}
        risk_objects.append(risk)
        short_desc = loader.format_text_list(risk.get("shortDescription", []))
        risk_entries.append({
            "id": risk_id,
            "title": risk.get("title", risk_id),
            "category": _normalize_category(risk.get("category", ""), "risks"),
            "summary": _compact_text(short_desc),
        })

    risk_title_by_id = {item["id"]: item["title"] for item in risk_entries}

    control_entries: list[dict[str, Any]] = []
    practice_entries: list[dict[str, Any]] = []
    sorted_controls = sorted(
        [c for c in controls if c and c.get("id")],
        key=lambda item: item.get("title", item.get("id", "")),
    )

    personas = getattr(loader, "personas", {}) or {}
    for control in sorted_controls:
        control_id = control.get("id", "")
        description = loader.format_text_list(control.get("description", []))
        mitigates = [
            risk_id for risk_id in control.get("risks", [])
            if risk_id in risk_title_by_id
        ]
        control_entries.append({
            "id": control_id,
            "title": control.get("title", control_id),
            "category": _normalize_category(control.get("category", ""), "controls"),
            "summary": _compact_text(description),
            "mitigatesRisks": mitigates,
            "mitigatesRiskTitles": [risk_title_by_id[risk_id] for risk_id in mitigates],
        })

        owner_roles = []
        for persona_id in control.get("personas", []):
            role_name = personas.get(persona_id, {}).get("title", persona_id)
            owner_roles.append(role_name)

        practice_entries.append({
            "id": control_id,
            "title": control.get("title", control_id),
            "practice": _first_sentence(description),
            "ownerRoles": owner_roles,
            "lifecycleStages": control.get("lifecycleStage", []),
        })

    framework_hits = _collect_framework_hits(risk_objects, sorted_controls)
    framework_meta = _load_frameworks(loader)
    recommended_tools: list[dict[str, Any]] = []
    for framework_id in sorted(framework_hits):
        hit = framework_hits[framework_id]
        framework = framework_meta.get(framework_id, {})
        recommended_tools.append({
            "id": framework_id,
            "name": framework.get("name", framework_id),
            "type": "framework",
            "description": _compact_text(framework.get("description", "")),
            "reference": framework.get("baseUri", ""),
            "mappedItems": sorted(hit["mappedItems"]),
            "sourcedFrom": sorted(hit["sources"]),
        })

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    generated_at = generated_at.replace("+00:00", "Z")

    return {
        "generatedAt": generated_at,
        "riskTier": {
            "label": vayu.get("label", "unknown"),
            "value": vayu.get("tier"),
            "escalationTriggers": list(vayu.get("escalatedRules", [])),
        },
        "counts": {
            "risks": len(risk_entries),
            "controls": len(control_entries),
            "practices": len(practice_entries),
            "recommendedTools": len(recommended_tools),
        },
        "risks": risk_entries,
        "controls": control_entries,
        "practices": practice_entries,
        "recommendedTools": recommended_tools,
    }


def summary_to_json(summary: dict[str, Any]) -> str:
    """Serialize export summary to pretty JSON."""
    return json.dumps(summary, indent=2)


def summary_to_markdown(summary: dict[str, Any]) -> str:
    """Render export summary in markdown for human-friendly sharing."""
    tier = summary.get("riskTier", {})
    counts = summary.get("counts", {})
    lines = [
        "# AI Risk Assessment Summary",
        "",
        f"- Generated at: {summary.get('generatedAt', '')}",
        f"- Risk tier: {str(tier.get('label', 'unknown')).upper()}",
        f"- Risks: {counts.get('risks', 0)}",
        f"- Controls: {counts.get('controls', 0)}",
        f"- Practices: {counts.get('practices', 0)}",
        f"- Recommended tools: {counts.get('recommendedTools', 0)}",
        "",
        "## Risks",
    ]

    risks = summary.get("risks", [])
    if not risks:
        lines.append("- None identified.")
    else:
        for risk in risks:
            category = risk.get("category", "Other")
            description = risk.get("summary", "")
            lines.append(
                f"- **{risk.get('id', '')} - {risk.get('title', '')}** ({category})"
            )
            if description:
                lines.append(f"  - {description}")

    lines += ["", "## Controls"]
    controls = summary.get("controls", [])
    if not controls:
        lines.append("- None mapped.")
    else:
        for control in controls:
            lines.append(
                f"- **{control.get('id', '')} - {control.get('title', '')}** "
                f"({control.get('category', 'Other')})"
            )
            if control.get("summary"):
                lines.append(f"  - {control['summary']}")
            if control.get("mitigatesRiskTitles"):
                joined = ", ".join(control["mitigatesRiskTitles"])
                lines.append(f"  - Mitigates: {joined}")

    lines += ["", "## Practices"]
    practices = summary.get("practices", [])
    if not practices:
        lines.append("- None available.")
    else:
        for practice in practices:
            lines.append(f"- **{practice.get('title', '')}**")
            if practice.get("practice"):
                lines.append(f"  - {practice['practice']}")
            if practice.get("ownerRoles"):
                lines.append(f"  - Owners: {', '.join(practice['ownerRoles'])}")
            if practice.get("lifecycleStages"):
                lines.append(f"  - Lifecycle: {', '.join(practice['lifecycleStages'])}")

    lines += ["", "## Recommended Tools"]
    tools = summary.get("recommendedTools", [])
    if not tools:
        lines.append("- None mapped from framework references.")
    else:
        for tool in tools:
            lines.append(f"- **{tool.get('name', tool.get('id', ''))}**")
            if tool.get("description"):
                lines.append(f"  - {tool['description']}")
            if tool.get("mappedItems"):
                lines.append(f"  - Mapped IDs: {', '.join(tool['mappedItems'])}")
            if tool.get("reference"):
                lines.append(f"  - Reference: {tool['reference']}")

    return "\n".join(lines).strip() + "\n"
