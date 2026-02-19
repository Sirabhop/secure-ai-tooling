"""Architecture diagram module for rendering Mermaid diagrams in Streamlit.

Loads pre-generated .mermaid files from risk-map/diagrams/ and renders them
using mermaid.js via Streamlit HTML components. Supports dynamic highlighting
of nodes based on assessment results.
"""

import re
import logging
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

_DIAGRAMS_DIR = Path(__file__).parent.parent / "risk-map" / "diagrams"

_DIAGRAM_FILES = {
    "component": "risk-map-graph.mermaid",
    "control": "controls-graph.mermaid",
    "risk": "controls-to-risk-graph.mermaid",
}

_DIAGRAM_META = {
    "component": {
        "title": "Component Architecture",
        "description": (
            "Shows how AI system components relate to each other across "
            "Infrastructure, Model, and Application layers."
        ),
        "height": 800,
    },
    "control": {
        "title": "Controls Mapping",
        "description": (
            "Maps security controls to the AI components they protect, "
            "organized by control category."
        ),
        "height": 1200,
    },
    "risk": {
        "title": "Risk → Control → Component",
        "description": (
            "Three-layer view: risks are mitigated by controls, which protect "
            "specific components."
        ),
        "height": 1600,
    },
}

_HIGHLIGHT_STYLE = "fill:#fff3cd,stroke:#ffc107,stroke-width:3px,color:#856404"

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)

_NODE_DEF_RE = re.compile(r"^\s+(\S+)\[.+\]")


def _strip_frontmatter(mermaid_code: str) -> str:
    """Remove YAML frontmatter (ELK config unsupported in browser mermaid.js)."""
    return _FRONTMATTER_RE.sub("", mermaid_code).strip()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mermaid_file(diagram_type: str) -> Optional[str]:
    """Load a pre-generated .mermaid file by diagram type.

    Returns None if the file doesn't exist or can't be read.
    """
    filename = _DIAGRAM_FILES.get(diagram_type)
    if not filename:
        logger.warning("Unknown diagram type: %s", diagram_type)
        return None

    filepath = _DIAGRAMS_DIR / filename
    if not filepath.exists():
        logger.warning("Mermaid file not found: %s", filepath)
        return None

    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("Failed to read %s: %s", filepath, e)
        return None


def _collect_defined_node_ids(mermaid_code: str) -> set[str]:
    """Extract all node IDs that have a bracket definition (e.g. ``nodeId[Title]``)."""
    ids: set[str] = set()
    for line in mermaid_code.split("\n"):
        m = _NODE_DEF_RE.match(line)
        if m:
            raw = m.group(1)
            ids.add(raw.split(":::")[0])
    return ids


def highlight_nodes(mermaid_code: str, node_ids: list[str]) -> str:
    """Highlight specific nodes by appending ``style`` directives.

    Uses Mermaid ``style nodeId ...`` lines at the end of the graph instead
    of mutating node definitions with ``:::class``.  This is compatible with
    all Mermaid versions and avoids syntax errors from inline class injection.
    """
    if not node_ids or not mermaid_code:
        return mermaid_code

    defined = _collect_defined_node_ids(mermaid_code)
    to_highlight = [nid for nid in dict.fromkeys(node_ids) if nid in defined]

    if not to_highlight:
        return mermaid_code

    style_lines = [f"    style {nid} {_HIGHLIGHT_STYLE}" for nid in to_highlight]
    return mermaid_code.rstrip() + "\n\n%% Assessment highlights\n" + "\n".join(style_lines) + "\n"


def render_mermaid(mermaid_code: str, height: int = 600, key: str = "mermaid") -> None:
    """Render a Mermaid diagram in Streamlit using mermaid.js CDN."""
    clean = _strip_frontmatter(mermaid_code)

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{ margin: 0; padding: 8px; background: transparent; overflow-x: auto; }}
  .mermaid {{ text-align: center; }}
  .mermaid svg {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<pre class="mermaid">
{clean}
</pre>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {{
      useMaxWidth: true,
      htmlLabels: true,
      curve: 'basis'
    }},
    maxTextSize: 100000
  }});
</script>
</body>
</html>"""

    components.html(html, height=height, scrolling=True)


def _get_assessment_highlights(loader) -> list[str]:
    """Collect node IDs to highlight from current session assessment results."""
    ids: list[str] = []

    for rid in st.session_state.get("relevant_risks", []):
        if rid not in ids:
            ids.append(rid)

    for cid in st.session_state.get("recommended_controls", []):
        if cid not in ids:
            ids.append(cid)
        ctrl = loader.get_control_details(cid)
        if ctrl:
            for comp in ctrl.get("components", []):
                if comp not in ("all", "none") and comp not in ids:
                    ids.append(comp)

    return ids


def render_architecture_page() -> None:
    """Render the full Architecture page in Streamlit."""
    st.title("🏗️ Architecture")
    st.markdown(
        "Explore the AI system architecture — components, security controls, "
        "and risk mappings — as interactive diagrams."
    )

    loader = st.session_state.get("data_loader")
    has_results = bool(st.session_state.get("answers"))
    highlight_ids = _get_assessment_highlights(loader) if has_results and loader else []

    tab_keys = list(_DIAGRAM_META.keys())
    tab_labels = [_DIAGRAM_META[k]["title"] for k in tab_keys]
    tabs = st.tabs(tab_labels)

    for tab, dtype in zip(tabs, tab_keys):
        with tab:
            meta = _DIAGRAM_META[dtype]
            st.caption(meta["description"])

            raw = load_mermaid_file(dtype)
            if raw is None:
                st.warning(
                    f"Diagram file not found: `{_DIAGRAM_FILES.get(dtype)}`. "
                    "Run the validator to generate diagrams."
                )
                continue

            code = highlight_nodes(raw, highlight_ids) if highlight_ids else raw

            if highlight_ids:
                n_risks = len(st.session_state.get("relevant_risks", []))
                n_ctrls = len(st.session_state.get("recommended_controls", []))
                st.caption(
                    f"Nodes highlighted in **yellow** reflect your assessment "
                    f"({n_risks} risks, {n_ctrls} controls)."
                )

            with st.expander("View Mermaid source", expanded=False):
                st.code(_strip_frontmatter(code), language="mermaid")

            render_mermaid(code, height=meta["height"], key=f"arch_{dtype}")
