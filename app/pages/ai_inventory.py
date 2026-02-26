"""AI Inventory intake form page – driven by ai-inventory.yaml schema."""
from __future__ import annotations

import logging
import uuid
from collections import ChainMap
from typing import Any, Dict, List, Mapping

import streamlit as st

from app.storage import (
    is_database_ready,
    load_ai_inventory_submission,
    save_ai_inventory_submission,
)
from app.ui_utils import render_page_header, render_step_indicator

logger = logging.getLogger(__name__)

# ── Session-state keys ───────────────────────────────────────────────────────
_STATE_KEY = "inventory_data"
_STEP_KEY = "inventory_step"
_REPEAT_KEY = "inventory_repeat_blocks"

# ── Placeholder catalogue options (replace with real lookups) ────────────────
_CATALOG_DEFAULTS: Dict[str, List[str]] = {
    "bankOrgList": [
        "Retail Banking",
        "Corporate Banking",
        "Wholesale Banking",
        "Digital Banking",
        "Wealth Management",
        "Operations",
        "Technology",
        "Risk Management",
        "Compliance",
        "Human Resources",
    ],
    "staffDirectory": [
        "Alice Wongsakul",
        "Bob Chaiyaphon",
        "Carol Suttirat",
        "David Kiatprasert",
        "Somchai P.",
        "Nattapong K.",
        "Parichat W.",
        "Kittisak T.",
        "Ariya S.",
        "Thanakrit M.",
    ],
    "systemCatalog": [
        "Core Banking",
        "CRM",
        "Data Warehouse",
        "API Gateway",
        "Document Management",
    ],
    "approvedModelCatalog": [
        "GPT-4o",
        "GPT-4o-mini",
        "Claude 3.5 Sonnet",
        "Claude 3.5 Haiku",
        "Gemini",
        "Gemini 1.5 Pro",
        "Gemini 1.5 Flash",
        "Gemini 2.5 Flash",
        "Gemini 2.5 Pro",
        "Gemini 3 Pro",
        "Gemini 3 Flash",
        "Gecko",
        "Chirp",
        "Journey",
        "Llama 3.1 70B",
        "Llama 3.1 8B",
        "Typhoon 1.5",
    ],
    "approvedEmbeddingModelCatalog": [
        "text-embedding-005",
        "text-embedding-3-large",
        "text-embedding-3-small",
        "text-embedding-ada-002",
        "voyage-3",
        "bge-m3",
    ],
    "approvedCloudRegions": [
        "asia-southeast1",
        "asia-southeast1 (Singapore)",
        "asia-southeast2 (Jakarta)",
        "us-central1",
        "us-east1",
        "europe-west1",
    ],
    "theEightFunctionTaxonomy": [
        "Customer eligibility or credit decisions",
        "Financial crime prevention",
        "Financial and risk management decision",
        "Customer influence and recommendations",
        "Customer communication and service",
        "Internal copilot or service with sensitive data",
        "Low risk internal productivity",
        "AI systems that influence other AI",
    ],
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _inv() -> Dict[str, Any]:
    """Shortcut to the inventory data dict in session state."""
    return st.session_state[_STATE_KEY]


def _resolve_options(field: dict) -> List[str]:
    """Build the option list for a select field."""
    if "options" in field:
        return list(field["options"])

    source = field.get("optionsSource", field.get("options_source", {}))
    src_type = source.get("type", "")
    opts = list(_CATALOG_DEFAULTS.get(src_type, []))
    if source.get("includeOther", source.get("include_other")):
        if "Other" not in opts:
            opts.append("Other")
    if source.get("includeUnknown", source.get("include_unknown")):
        if "Unknown" not in opts:
            opts.append("Unknown")
    return opts


def _eval_condition(
    cond: dict,
    data: Mapping[str, Any],
    repeat_blocks: dict[str, list] | None = None,
    flags: dict[str, Any] | None = None,
) -> bool:
    """Evaluate a single visibility/rule condition against form data and flags.

    Supports ``field`` conditions (match against form data) and ``flag``
    conditions (match against computed rule flags).

    *data* may be a ChainMap (row-local → global) so that repeating-block
    fields can reference both intra-row keys and top-level routing keys.

    When *repeat_blocks* is provided, fields not in data are checked across
    all repeating-block rows (any row match satisfies the condition).
    """
    # Flag conditions (used by step visibility driven by rules engine)
    if "flag" in cond:
        flag_value = (flags or {}).get(cond["flag"])
        if "equals" in cond:
            return flag_value == cond["equals"]
        return False

    field_key = cond.get("field", "")
    value = data.get(field_key)

    # If field not in main data, check repeating blocks
    if value is None and repeat_blocks:
        for rows in repeat_blocks.values():
            for row in rows:
                val = row.get(field_key)
                if val is not None:
                    if "equals" in cond and val == cond["equals"]:
                        return True
                    if "notEquals" in cond or "not_equals" in cond:
                        not_val = cond.get("notEquals", cond.get("not_equals"))
                        if val != not_val:
                            return True
                    if "includes" in cond:
                        if isinstance(val, list) and cond["includes"] in val:
                            return True
                        if val == cond["includes"]:
                            return True
        return False

    if "equals" in cond:
        return value == cond["equals"]
    if "notEquals" in cond or "not_equals" in cond:
        not_val = cond.get("notEquals", cond.get("not_equals"))
        return value != not_val
    if "includes" in cond:
        if isinstance(value, list):
            return cond["includes"] in value
        return value == cond["includes"]
    return False


def _eval_when(
    when: dict,
    data: Mapping[str, Any],
    repeat_blocks: dict | None = None,
    flags: dict | None = None,
) -> bool:
    """Evaluate a when clause (any/all conditions) from rules or visibilityLogic."""
    if not when:
        return False
    if "any" in when:
        return any(_eval_condition(c, data, repeat_blocks, flags=flags) for c in when["any"])
    if "all" in when:
        return all(_eval_condition(c, data, repeat_blocks, flags=flags) for c in when["all"])
    return False


def _is_visible(field: dict, data: Mapping[str, Any]) -> bool:
    """Check whether a field should be shown based on visibleWhen rules."""
    vis = field.get("visibleWhen", field.get("visible_when"))
    if not vis:
        return True
    if "any" in vis:
        return any(_eval_condition(c, data) for c in vis["any"])
    if "all" in vis:
        return all(_eval_condition(c, data) for c in vis["all"])
    return True


def _get_repeat_blocks_data() -> dict[str, list]:
    """Collect repeating-block rows from session state."""
    out: dict[str, list] = {}
    for k, v in st.session_state.items():
        if isinstance(k, str) and k.startswith(_REPEAT_KEY) and isinstance(v, list):
            block_id = k.replace(f"{_REPEAT_KEY}_", "")
            out[block_id] = v
    return out


def _compute_flags(
    schema: dict,
    data: Mapping[str, Any],
    repeat_blocks: dict[str, list] | None = None,
) -> dict[str, Any]:
    """Evaluate top-level rules from the schema and return computed flags.

    Rules are processed top-to-bottom; later rules overwrite earlier flags
    (``lastWins`` per ``ruleEvaluation.conflictResolution.flags``).
    """
    defaults = schema.get("flags", {}).get("defaults", {})
    flags: dict[str, Any] = dict(defaults)

    for rule in schema.get("rules", []):
        when = rule.get("when")
        set_flags = rule.get("setFlags")
        if set_flags and when and _eval_when(when, data, repeat_blocks):
            flags.update(set_flags)

    return flags


def _compute_step_states(
    schema: dict,
    data: Mapping[str, Any],
    repeat_blocks: dict[str, list] | None = None,
) -> dict[str, dict]:
    """Evaluate rules that carry ``stepState`` and return per-step states.

    Respects ``ruleEvaluation.conflictResolution.requiredness: requiredWins``.
    """
    conflict = schema.get("ruleEvaluation", {}).get("conflictResolution", {})
    required_wins = conflict.get("requiredness") == "requiredWins"

    raw: dict[str, dict] = {}

    for rule in schema.get("rules", []):
        step_state = rule.get("stepState")
        if not step_state:
            continue
        when = rule.get("when")
        if not when or not _eval_when(when, data, repeat_blocks):
            continue
        step_id = step_state.get("stepId", "")
        if not step_id:
            continue

        if step_id not in raw:
            raw[step_id] = {"required_values": [], "collapsedByDefault": None}

        req = step_state.get("required")
        if req is not None:
            raw[step_id]["required_values"].append(req)

        collapsed = step_state.get("collapsedByDefault")
        if collapsed is not None:
            raw[step_id]["collapsedByDefault"] = collapsed

    resolved: dict[str, dict] = {}
    for step_id, state in raw.items():
        req_values = state["required_values"]
        if req_values:
            resolved_req = any(v is True for v in req_values) if required_wins else req_values[-1]
        else:
            resolved_req = None
        resolved[step_id] = {
            "required": resolved_req,
            "collapsedByDefault": state["collapsedByDefault"],
        }

    return resolved


def _get_hidden_steps_from_display_rules(
    steps: List[dict],
    data: Mapping[str, Any],
    repeat_blocks: dict[str, list],
) -> set[str]:
    """From the first step's displayRules, compute steps that must be hidden."""
    hidden: set[str] = set()
    first_step_id = steps[0].get("id", "") if steps else ""
    for step in steps:
        if step.get("id") != first_step_id:
            continue
        for rule in step.get("displayRules", step.get("display_rules", [])):
            when = rule.get("when", {})
            hide_steps = rule.get("hideSteps", rule.get("hide_steps", []))
            if hide_steps and _eval_when(when, data, repeat_blocks):
                hidden.update(hide_steps)
    return hidden


def _is_step_visible(
    step: dict,
    data: Mapping[str, Any],
    hidden_steps: set[str] | None = None,
    repeat_blocks: dict[str, list] | None = None,
    flags: dict[str, Any] | None = None,
) -> bool:
    """Check step-level visibility using displayRules hideSteps, visibilityLogic, and flags."""
    step_id = step.get("id", "")
    if hidden_steps and step_id in hidden_steps:
        return False

    vis = step.get("visibilityLogic", step.get("visibility_logic", {}))
    shown_when = vis.get("shownWhen", vis.get("shown_when"))
    optional_when = vis.get("optionalWhen", vis.get("optional_when"))

    if shown_when:
        if "any" in shown_when:
            return any(_eval_condition(c, data, repeat_blocks, flags=flags) for c in shown_when["any"])
        if "all" in shown_when:
            return all(_eval_condition(c, data, repeat_blocks, flags=flags) for c in shown_when["all"])

    if optional_when:
        return True

    if not shown_when and not optional_when:
        return True

    return False


def _is_step_optional(
    step: dict,
    data: Mapping[str, Any],
    step_states: dict[str, dict] | None = None,
    repeat_blocks: dict[str, list] | None = None,
) -> bool:
    """Check if a step is optional based on rule-computed step states and visibilityLogic."""
    step_id = step.get("id", "")

    # Rule-computed step states (respects requiredWins conflict resolution)
    if step_states and step_id in step_states:
        state = step_states[step_id]
        if state.get("required") is True:
            return False
        if state.get("required") is False or state.get("collapsedByDefault") is True:
            return True

    # Fallback to visibilityLogic.optionalWhen
    vis = step.get("visibilityLogic", step.get("visibility_logic", {}))
    optional_when = vis.get("optionalWhen", vis.get("optional_when"))
    if optional_when:
        if "any" in optional_when:
            return any(_eval_condition(c, data, repeat_blocks) for c in optional_when["any"])
        if "all" in optional_when:
            return all(_eval_condition(c, data, repeat_blocks) for c in optional_when["all"])
    return False


# ── Relevance filtering ─────────────────────────────────────────────────────

# IDs of the routing selectors — always shown regardless of their own relevance tag
_ROUTING_FIELD_KEYS = frozenset({"modelCreator", "modelUsage"})


def _get_active_relevance(data: Mapping[str, Any]) -> set[str]:
    """Derive active relevance tracks from the routing answers in step 1.

    Tracks:
      "neither"       – always active (general-info fields).
      "modelCreator"  – active when user IS creating / training a model.
      "modelUsage"    – active once the user has selected a usage mode.
      "both"          – active when *either* individual track is active.
    """
    active: set[str] = {"neither"}

    creator_answer = data.get("modelCreator")
    usage_answer = data.get("modelUsage")

    if creator_answer and creator_answer != "No model creation, use existing model":
        active.add("modelCreator")

    if usage_answer:
        active.add("modelUsage")

    if "modelCreator" in active or "modelUsage" in active:
        active.add("both")

    return active


def _normalize_relevance(r: str) -> str:
    """Normalize relevance to camelCase for comparison."""
    if r == "model_creator":
        return "modelCreator"
    if r == "model_usage":
        return "modelUsage"
    return r


def _is_relevant(field: dict, active_relevance: set[str]) -> bool:
    """Return True if *field* passes the relevance filter."""
    fkey = field.get("key", "")
    if fkey in _ROUTING_FIELD_KEYS:
        return True
    relevance = _normalize_relevance(field.get("relevance", "neither"))
    return relevance in active_relevance


# ── Field renderer ───────────────────────────────────────────────────────────

def _render_field(
    field: dict,
    data: Dict[str, Any],
    key_prefix: str = "",
    lookup_data: Mapping[str, Any] | None = None,
    active_relevance: set[str] | None = None,
) -> None:
    """Render a single form field and write value into *data*.

    *lookup_data* is used for visibility evaluation (e.g. ChainMap for
    repeating blocks that need access to global form data).
    """
    if lookup_data is None:
        lookup_data = data

    if active_relevance is not None and not _is_relevant(field, active_relevance):
        return

    fkey = field.get("key", "")
    data_key = fkey
    ftype = field.get("type", "textShort") or "textShort"
    # Normalize legacy snake_case types
    _type_map = {
        "auto_id": "autoId", "text_short": "textShort", "text_multiline": "textMultiline",
        "text_optional": "textOptional", "number_optional": "numberOptional",
        "select_one": "selectOne", "select_many": "selectMany",
    }
    ftype = _type_map.get(ftype, ftype)
    label = field.get("label", fkey)
    guidance = field.get("guidance")
    widget_key = f"{key_prefix}{fkey}"

    if not _is_visible(field, lookup_data):
        return

    # Auto-generated ID
    if ftype == "autoId":
        if not data.get(data_key):
            data[data_key] = f"UC-{uuid.uuid4().hex[:8].upper()}"
        st.text_input(label, value=data[data_key], disabled=True, key=widget_key, help=guidance)
        return

    # Text short
    if ftype == "textShort":
        data[data_key] = st.text_input(label, value=data.get(data_key, ""), key=widget_key, help=guidance)
        return

    # Text multiline
    if ftype == "textMultiline":
        data[data_key] = st.text_area(label, value=data.get(data_key, ""), key=widget_key, help=guidance, height=120)
        return

    # Text optional
    if ftype == "textOptional":
        data[data_key] = st.text_input(f"{label} *(optional)*", value=data.get(data_key, ""), key=widget_key, help=guidance)
        return

    # Number optional
    if ftype == "numberOptional":
        current = data.get(data_key)
        data[data_key] = st.number_input(
            f"{label} *(optional)*",
            value=float(current) if current is not None else 0.0,
            format="%.2f",
            key=widget_key,
            help=guidance,
        )
        return

    # Select one (dropdown)
    if ftype == "selectOne":
        options = _resolve_options(field)
        current = data.get(data_key)
        # Preserve prefilled values not in catalog (e.g. from mock scenarios)
        if current and current not in options and current not in ("— Select —", ""):
            options = [current] + [o for o in options if o != current]
        display_options = ["— Select —"] + options
        idx = (options.index(current) + 1) if current in options else 0
        selected = st.selectbox(label, options=display_options, index=idx, key=widget_key, help=guidance)
        data[data_key] = selected if selected != "— Select —" else None
        return

    # Select many (multi-select)
    if ftype == "selectMany":
        options = _resolve_options(field)
        current = data.get(data_key) or []
        if not isinstance(current, list):
            current = [current]
        # Preserve prefilled values not in catalog (e.g. from mock scenarios)
        extras = [c for c in current if c and c not in options]
        if extras:
            options = extras + [o for o in options if o not in extras]
        valid_current = [c for c in current if c in options]

        selected = st.multiselect(label, options=options, default=valid_current, key=widget_key, help=guidance)

        # Enforce mutual exclusivity constraints
        constraints = field.get("constraints", {})
        groups = constraints.get("mutuallyExclusiveGroups", constraints.get("mutually_exclusive_groups", []))
        for group in groups:
            exclusive_opts = set(group.get("options", []))
            other_opts = set(group.get("exclusiveWith", group.get("exclusive_with", [])))
            if (exclusive_opts & set(selected)) and (other_opts & set(selected)):
                st.warning(
                    f"'{', '.join(exclusive_opts & set(selected))}' cannot be combined "
                    f"with other options. Please adjust your selection."
                )

        data[data_key] = selected
        return


# ── Section / repeating-block renderers ──────────────────────────────────────

def _render_fields(
    fields: List[dict],
    data: Dict[str, Any],
    prefix: str = "",
    lookup_data: Mapping[str, Any] | None = None,
    active_relevance: set[str] | None = None,
) -> None:
    """Render a list of fields."""
    for field in fields:
        _render_field(
            field, data, key_prefix=prefix, lookup_data=lookup_data,
            active_relevance=active_relevance,
        )


def _render_section(
    section: dict,
    data: Dict[str, Any],
    prefix: str = "",
    lookup_data: Mapping[str, Any] | None = None,
    active_relevance: set[str] | None = None,
) -> None:
    """Render a titled section with its fields."""
    title = section.get("title", "")
    if title:
        st.markdown(f"#### {title}")
    sec_fields = section.get("fields", [])
    _render_fields(
        sec_fields, data, prefix=prefix, lookup_data=lookup_data,
        active_relevance=active_relevance,
    )


def _render_repeating_block(
    block: dict,
    global_data: Dict[str, Any],
    active_relevance: set[str] | None = None,
) -> None:
    """Render a repeating block. Each row is an independent dict.

    Visibility conditions inside the row are evaluated against a ChainMap
    of (row_data, global_data) so fields can reference both.
    """
    block_id = block.get("id", "unknown")
    title = block.get("title", "")
    guidance = block.get("guidance", "")
    fields_spec = block.get("fields", [])
    min_items = block.get("minItems", block.get("min_items", 0))
    repeat_key = f"{_REPEAT_KEY}_{block_id}"

    # Label key used to derive a friendly expander name
    name_field_key = _find_name_field(fields_spec)

    if repeat_key not in st.session_state:
        st.session_state[repeat_key] = [{} for _ in range(max(min_items, 0))]

    rows: list = st.session_state[repeat_key]

    # Ensure min_items
    while len(rows) < min_items:
        rows.append({})

    st.markdown(f"#### {title}")
    if guidance:
        st.caption(guidance)

    if not rows:
        st.info("No entries yet. Click **Add entry** below to start.")

    rows_to_delete: list[int] = []

    for row_idx, row_data in enumerate(rows):
        row_label = _row_expander_label(row_idx, row_data, name_field_key)
        merged = ChainMap(row_data, global_data)
        with st.expander(row_label, expanded=(row_idx == len(rows) - 1)):
            prefix = f"rep_{block_id}_{row_idx}_"
            _render_fields(fields_spec, row_data, prefix=prefix, lookup_data=merged, active_relevance=active_relevance)
            can_delete = len(rows) > min_items
            if can_delete and st.button("Remove this entry", key=f"del_{block_id}_{row_idx}"):
                rows_to_delete.append(row_idx)

    if rows_to_delete:
        for idx in sorted(rows_to_delete, reverse=True):
            rows.pop(idx)
        st.rerun()

    if st.button("Add entry", key=f"add_{block_id}"):
        rows.append({})
        st.rerun()


def _find_name_field(fields: List[dict]) -> str | None:
    """Return the key of the first textShort field (used as a human label)."""
    for f in fields:
        t = f.get("type", "")
        if t in ("textShort", "text_short"):
            return f.get("key")
    return None


def _row_expander_label(idx: int, row_data: dict, name_key: str | None) -> str:
    """Build a descriptive expander label for a repeating-block row."""
    base = f"Entry {idx + 1}"
    if name_key:
        name = row_data.get(name_key, "")
        if name:
            return f"{base} — {name}"
    return base


def _render_db_controls(data: Dict[str, Any]) -> None:
    """Render load-by-ID controls when Postgres is configured."""
    if not is_database_ready():
        st.caption(
            "PostgreSQL persistence is disabled. Set `DATABASE_URL` or "
            "`PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD` to enable save/load by ID."
        )
        return

    with st.expander("PostgreSQL persistence", expanded=False):
        current_id = data.get("useCaseId")
        if current_id:
            st.caption(f"Current inventory ID: `{current_id}`")

        load_id = st.text_input(
            "Load inventory by ID",
            key="inv_db_load_id",
            placeholder="UC-XXXXXXXX",
        ).strip()

        if st.button("Load Inventory", use_container_width=True, key="inv_db_load_button"):
            if not load_id:
                st.warning("Please enter a use case ID.")
                return

            try:
                record = load_ai_inventory_submission(load_id)
            except Exception:
                logger.exception("Failed loading AI inventory id=%s", load_id)
                st.error("Failed to load record from PostgreSQL.")
                return

            if not record:
                st.warning(f"No inventory record found for ID `{load_id}`.")
                return

            st.session_state[_STATE_KEY] = record.get("payload", {})
            for key in list(st.session_state.keys()):
                if isinstance(key, str) and key.startswith(_REPEAT_KEY):
                    del st.session_state[key]

            repeat_blocks = record.get("repeat_blocks", {})
            for block_id, rows in repeat_blocks.items():
                if isinstance(rows, list):
                    st.session_state[f"{_REPEAT_KEY}_{block_id}"] = rows
                    st.session_state[_STATE_KEY][f"_repeat_{block_id}"] = rows

            st.session_state[_STEP_KEY] = 0
            st.success(f"Loaded inventory record `{load_id}`.")
            st.rerun()


# ── Step renderer ────────────────────────────────────────────────────────────

def _render_step(step: dict, data: Dict[str, Any]) -> None:
    """Render all content inside a step (fields, sections, repeating blocks)."""
    step_id = step.get("id", "")
    active_rel = _get_active_relevance(data)

    # Top-level fields (first step with direct fields)
    top_fields = step.get("fields", [])
    if top_fields:
        _render_fields(top_fields, data, prefix=f"{step_id}_", active_relevance=active_rel)

    # Named sections – widget key prefix includes section_id for uniqueness
    for section in step.get("sections", []):
        sec_id = section.get("id", "")
        sec_prefix = f"{step_id}_{sec_id}_" if sec_id else f"{step_id}_"
        _render_section(
            section, data, prefix=sec_prefix, active_relevance=active_rel,
        )

    # Repeating blocks – pass global data for cross-step visibility
    for block in step.get("repeatingBlocks", step.get("repeating_blocks", [])):
        _render_repeating_block(block, global_data=data, active_relevance=active_rel)


# ── Main page ────────────────────────────────────────────────────────────────

def render_ai_inventory() -> None:
    """Render the AI Inventory intake form."""
    render_page_header(
        "📋", "AI Inventory",
        "Use-case intake form. Most fields can be prefilled from inventory and only require review or edit."
    )

    loader = st.session_state.data_loader
    schema = loader.ai_inventory_schema
    if not schema:
        st.error("Could not load AI inventory schema (ai-inventory.yaml).")
        return

    steps: List[dict] = schema.get("steps", [])
    if not steps:
        st.warning("No steps defined in the schema.")
        return

    # Ensure session state containers exist
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = {}
    if _STEP_KEY not in st.session_state:
        st.session_state[_STEP_KEY] = 0

    data = _inv()
    _render_db_controls(data)
    repeat_blocks = _get_repeat_blocks_data()
    hidden_steps = _get_hidden_steps_from_display_rules(steps, data, repeat_blocks)

    # Evaluate top-level rules to compute flags and per-step states
    flags = _compute_flags(schema, data, repeat_blocks)
    step_states = _compute_step_states(schema, data, repeat_blocks)

    # Build list of visible steps (displayRules hideSteps + per-step visibilityLogic + flags)
    visible_steps: List[dict] = [
        s for s in steps
        if _is_step_visible(s, data, hidden_steps, repeat_blocks, flags=flags)
    ]
    if not visible_steps:
        st.error("No visible steps for the current answers. Please reset the form.")
        return
    step_labels = [s.get("title", s.get("id", "")) for s in visible_steps]

    current_idx = st.session_state[_STEP_KEY]
    current_idx = max(0, min(current_idx, len(visible_steps) - 1))
    st.session_state[_STEP_KEY] = current_idx

    # Step indicator
    render_step_indicator(step_labels, current_idx)

    # Progress
    _render_progress_summary(visible_steps, data)

    st.markdown("---")

    # Render current step
    current_step = visible_steps[current_idx]
    step_title = current_step.get("title", "")
    is_optional = _is_step_optional(current_step, data, step_states=step_states, repeat_blocks=repeat_blocks)

    st.subheader(f"Step {current_idx + 1}: {step_title}")
    if is_optional:
        st.info("This step is optional based on your earlier answers.")

    _render_step(current_step, data)

    # Navigation
    st.markdown("---")
    col_left, _, col_right = st.columns([1, 3, 1])

    with col_left:
        if current_idx > 0 and st.button("← Back", use_container_width=True, key="inv_back"):
            st.session_state[_STEP_KEY] = current_idx - 1
            st.rerun()

    with col_right:
        if current_idx < len(visible_steps) - 1:
            if st.button("Next →", use_container_width=True, type="primary", key="inv_next"):
                st.session_state[_STEP_KEY] = current_idx + 1
                st.rerun()
        else:
            if st.button("Submit", use_container_width=True, type="primary", key="inv_submit"):
                _handle_submit(visible_steps, data)

    # Reset
    if any(v for v in data.values() if v):
        st.markdown("---")
        if st.button("Reset form", type="secondary", key="inv_reset"):
            st.session_state[_STATE_KEY] = {}
            st.session_state[_STEP_KEY] = 0
            for k in list(st.session_state.keys()):
                if k.startswith(_REPEAT_KEY):
                    del st.session_state[k]
            st.rerun()


# ── Progress / validation helpers ────────────────────────────────────────────

def _render_progress_summary(visible_steps: List[dict], data: Dict[str, Any]) -> None:
    """Show a compact progress bar counting filled fields (non-repeating only)."""
    active_rel = _get_active_relevance(data)
    total = 0
    filled = 0
    for step in visible_steps:
        for field in _collect_fields(step):
            t = field.get("type", "")
            if t in ("autoId", "auto_id"):
                continue
            if not _is_relevant(field, active_rel):
                continue
            if not _is_visible(field, data):
                continue
            total += 1
            data_key = field.get("_data_key", field.get("key", ""))
            val = data.get(data_key)
            if val is not None and val != "" and val != []:
                filled += 1

    if total > 0:
        st.progress(filled / total)
        st.caption(f"{filled} / {total} fields completed")


def _collect_fields(step: dict, include_repeating: bool = False) -> List[dict]:
    """Collect all field dicts from a step with their data_key for lookup."""
    out: List[dict] = []
    for f in step.get("fields", []):
        out.append({**f, "_data_key": f.get("key", "")})
    for sec in step.get("sections", []):
        for f in sec.get("fields", []):
            out.append({**f, "_data_key": f.get("key", "")})
    if include_repeating:
        for block in step.get("repeatingBlocks", step.get("repeating_blocks", [])):
            for f in block.get("fields", []):
                out.append({**f, "_data_key": f.get("key", "")})
    return out


def _handle_submit(visible_steps: List[dict], data: Dict[str, Any]) -> None:
    """Validate and finalize the form."""
    active_rel = _get_active_relevance(data)
    missing: List[str] = []
    for step in visible_steps:
        for field in _collect_fields(step):
            ftype = field.get("type", "")
            if ftype in ("autoId", "auto_id", "textOptional", "text_optional", "numberOptional", "number_optional"):
                continue
            if not _is_relevant(field, active_rel):
                continue
            if not _is_visible(field, data):
                continue
            data_key = field.get("_data_key", field.get("key", ""))
            val = data.get(data_key)
            if val is None or val == "" or val == []:
                missing.append(field.get("label", field.get("key", "")))

    if missing:
        st.warning(
            f"**{len(missing)} field(s) still empty.** You can still submit, "
            "but filling them gives a more complete record."
        )
        with st.expander("Show missing fields"):
            for m in missing:
                st.markdown(f"- {m}")

    # Collect repeating block data into the main data dict
    repeat_blocks = _get_repeat_blocks_data()
    for block_id, rows in repeat_blocks.items():
        data[f"_repeat_{block_id}"] = rows

    logger.info("AI inventory submitted: use_case=%s, models=%d", data.get("useCaseName"), len(data.get("_repeat_block4Models", [])))
    if is_database_ready():
        try:
            persisted_id = save_ai_inventory_submission(data, repeat_blocks)
            st.success(
                f"Inventory entry saved to PostgreSQL with ID `{persisted_id}`. "
                "You can load it later by ID."
            )
            return
        except Exception:
            logger.exception("Failed saving AI inventory to PostgreSQL")
            st.error("Could not save to PostgreSQL. Data remains in session for this browser tab.")
            return

    st.success(
        "Inventory entry saved in session state only. Configure PostgreSQL "
        "to persist and retrieve by ID."
    )
