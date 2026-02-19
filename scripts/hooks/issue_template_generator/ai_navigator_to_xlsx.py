#!/usr/bin/env python3
"""Convert ai-inventory.yaml schema to Excel (.xlsx) in risk-map/excels."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

# Paths relative to repo root
DEFAULT_INPUT = Path("risk-map/yaml/ai-inventory.yaml")
DEFAULT_OUTPUT_DIR = Path("risk-map/excels")


def _merge_steps_by_id(steps: list) -> list[dict]:
    """Merge steps with duplicate IDs into a single step (combines sections)."""
    by_id: dict[str, dict] = {}
    order: list[str] = []

    for step in steps:
        step_id = step.get("id", "")
        if not step_id:
            continue
        if step_id not in by_id:
            by_id[step_id] = dict(step)
            by_id[step_id]["sections"] = list(step.get("sections", []))
            by_id[step_id]["fields"] = list(step.get("fields", []))
            blocks = step.get("repeatingBlocks", step.get("repeating_blocks", []))
            by_id[step_id]["repeatingBlocks"] = list(blocks)
            order.append(step_id)
        else:
            merged = by_id[step_id]
            merged["sections"].extend(step.get("sections", []))
            merged["fields"].extend(step.get("fields", []))
            blocks = step.get("repeatingBlocks", step.get("repeating_blocks", []))
            merged["repeatingBlocks"].extend(blocks)

    return [by_id[sid] for sid in order]


def _iter_fields(steps: list) -> list[dict]:
    """Extract all fields from steps, flattening sections and repeating blocks."""
    rows = []
    for step in steps:
        step_id = step.get("id", "")
        step_title = step.get("title", "")
        section_id = section_title = block_id = block_title = ""

        # Direct fields
        for f in step.get("fields", []):
            rows.append(_field_row(step_id, step_title, section_id, section_title,
                                   block_id, block_title, f))

        # Section fields
        for sec in step.get("sections", []):
            section_id = sec.get("id", "")
            section_title = sec.get("title", "")
            for f in sec.get("fields", []):
                rows.append(_field_row(step_id, step_title, section_id, section_title,
                                       block_id, block_title, f))

        # Repeating block fields (reset section context)
        section_id = section_title = ""
        for block in step.get("repeatingBlocks", []):
            block_id = block.get("id", "")
            block_title = block.get("title", "")
            for f in block.get("fields", []):
                rows.append(_field_row(step_id, step_title, section_id, section_title,
                                       block_id, block_title, f))

    return rows


def _field_row(step_id: str, step_title: str, section_id: str, section_title: str,
               block_id: str, block_title: str, field: dict) -> dict:
    """Build a flat dict for one field."""
    opts = field.get("options")
    opts_src = field.get("optionsSource") or field.get("options_source")
    opts_str = ""
    if opts:
        opts_str = " | ".join(str(o) for o in opts)
    elif opts_src:
        opts_str = f"[{opts_src.get('type', '')}]"

    visible = field.get("visibleWhen")
    visible_str = yaml.dump(visible, default_flow_style=True, sort_keys=False).strip() if visible else ""

    constraints = field.get("constraints")
    constraints_str = yaml.dump(constraints, default_flow_style=True, sort_keys=False).strip() if constraints else ""

    return {
        "step_id": step_id,
        "step_title": step_title,
        "section_id": section_id,
        "section_title": section_title,
        "block_id": block_id,
        "block_title": block_title,
        "key": field.get("key", ""),
        "label": field.get("label", ""),
        "type": field.get("type", ""),
        "relevance": field.get("relevance", ""),
        "options": opts_str,
        "guidance": field.get("guidance", ""),
        "visible_when": visible_str,
        "constraints": constraints_str,
        "other_detail_field": field.get("otherDetailField") or field.get("other_detail_field", ""),
        "immutable": _bool_str(constraints, "immutable"),
        "required": _bool_str(constraints, "required"),
    }


def _bool_str(constraints: dict | None, key: str) -> str:
    if not constraints or not isinstance(constraints, dict):
        return ""
    v = constraints.get(key)
    return "yes" if v is True else ("no" if v is False else "")


def _to_excel(data: dict, out_path: Path) -> None:
    """Write YAML data to Excel using pandas."""
    import pandas as pd

    out_path.parent.mkdir(parents=True, exist_ok=True)

    steps = _merge_steps_by_id(data.get("steps", []))

    def _write_sheet(df: pd.DataFrame, writer: pd.ExcelWriter, sheet_name: str) -> None:
        """Insert a 1-based running number column and write the sheet."""
        df.insert(0, "#", range(1, len(df) + 1))
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        # Fields sheet (main)
        rows = _iter_fields(steps)
        if rows:
            _write_sheet(pd.DataFrame(rows), writer, "Fields")

        # Metadata sheet
        meta = {
            "schemaVersion": [data.get("schemaVersion", "")],
            "purpose": [data.get("purpose", "")],
            "relevance_labels": [", ".join(data.get("relevanceLabels", []))],
            "prefill_sources": [", ".join(data.get("prefillSources", []))],
        }
        _write_sheet(pd.DataFrame(meta), writer, "Metadata")

        # Taxonomy sheet (theEightFunctionTaxonomy)
        taxonomy = data.get("theEightFunctionTaxonomy", [])
        if taxonomy:
            tax_rows = []
            for t in taxonomy:
                tax_rows.append({
                    "id": t.get("id", ""),
                    "label": t.get("label", ""),
                    "decisionImpact": t.get("decisionImpact", ""),
                    "exampleUseCase": " | ".join(t.get("exampleUseCase", [])),
                })
            _write_sheet(pd.DataFrame(tax_rows), writer, "Taxonomy")

        # Rules sheet
        rules = data.get("rules", [])
        if rules:
            rule_rows = []
            for r in rules:
                set_flags = r.get("setFlags", {})
                step_state = r.get("stepState", {})
                when = r.get("when", {})
                rule_rows.append({
                    "id": r.get("id", ""),
                    "description": r.get("description", ""),
                    "setFlags": yaml.dump(set_flags, default_flow_style=True, sort_keys=False).strip() if set_flags else "",
                    "stepState": yaml.dump(step_state, default_flow_style=True, sort_keys=False).strip() if step_state else "",
                    "when": yaml.dump(when, default_flow_style=True, sort_keys=False).strip() if when else "",
                })
            _write_sheet(pd.DataFrame(rule_rows), writer, "Rules")

        # Flags defaults sheet
        flag_defaults = data.get("flags", {}).get("defaults", {})
        if flag_defaults:
            _write_sheet(pd.DataFrame([flag_defaults]), writer, "FlagDefaults")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert ai-inventory.yaml to Excel")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT,
                        help=f"Input YAML path (default: {DEFAULT_INPUT})")
    parser.add_argument("--output-dir", "-o", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--name", "-n", default="ai-inventory",
                        help="Output filename without extension (default: ai-inventory)")
    args = parser.parse_args()

    input_path = args.input if args.input.is_absolute() else Path.cwd() / args.input
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        return 1

    out_path = args.output_dir if args.output_dir.is_absolute() else Path.cwd() / args.output_dir
    out_path = out_path / f"{args.name}.xlsx"

    with open(input_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _to_excel(data, out_path)
    print(f"Written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
