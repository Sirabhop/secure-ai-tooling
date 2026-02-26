"""Tests for assessment export summary generation."""

from app.export_summary import build_assessment_export_summary, summary_to_markdown


class _FakeLoader:
    """Small loader stub used for export summary tests."""

    personas = {
        "personaModelCreator": {"title": "Model Creator"},
        "personaModelConsumer": {"title": "Model Consumer"},
    }

    def __init__(self):
        self._risks = {
            "R1": {
                "id": "R1",
                "title": "Prompt Injection",
                "category": "risksRuntimeInputSecurity",
                "shortDescription": ["Untrusted input changes model behavior."],
                "mappings": {"owasp-top10-llm": ["LLM01"]},
            }
        }

    def get_risk_details(self, risk_id):
        return self._risks.get(risk_id)

    def format_text_list(self, text_list):
        return " ".join(str(item) for item in text_list if item)

    def load_yaml(self, filename):
        if filename != "frameworks.yaml":
            return {}
        return {
            "frameworks": [
                {
                    "id": "owasp-top10-llm",
                    "name": "OWASP Top 10 for LLM",
                    "description": "Top 10 critical risks for LLM applications.",
                    "baseUri": "https://owasp.org/www-project-top-10-for-large-language-model-applications",
                },
                {
                    "id": "nist-ai-rmf",
                    "name": "NIST AI RMF",
                    "description": "Risk management framework for AI systems.",
                    "baseUri": "https://www.nist.gov/itl/ai-risk-management-framework",
                },
            ]
        }


def test_build_assessment_export_summary_includes_expected_sections():
    """Summary contains risks, controls, practices, and recommended tools."""
    loader = _FakeLoader()
    vayu = {"label": "medium", "tier": 2, "escalatedRules": ["High autonomy"]}
    controls = [
        {
            "id": "C1",
            "title": "Input Validation",
            "category": "controlsApplication",
            "description": [
                "Validate prompts before execution. Use strict policy checks for untrusted content."
            ],
            "personas": ["personaModelCreator"],
            "lifecycleStage": ["runtime"],
            "risks": ["R1"],
            "mappings": {"nist-ai-rmf": ["GV-1.1"]},
        }
    ]

    summary = build_assessment_export_summary(loader, vayu, ["R1"], controls)

    assert summary["riskTier"]["label"] == "medium"
    assert summary["counts"]["risks"] == 1
    assert summary["counts"]["controls"] == 1
    assert summary["counts"]["practices"] == 1
    assert summary["counts"]["recommendedTools"] == 2

    assert summary["risks"][0]["title"] == "Prompt Injection"
    assert summary["controls"][0]["mitigatesRiskTitles"] == ["Prompt Injection"]
    assert summary["practices"][0]["practice"] == "Validate prompts before execution."
    assert summary["practices"][0]["ownerRoles"] == ["Model Creator"]

    tool_names = {item["name"] for item in summary["recommendedTools"]}
    assert "OWASP Top 10 for LLM" in tool_names
    assert "NIST AI RMF" in tool_names


def test_summary_to_markdown_renders_key_sections():
    """Markdown formatter renders all required top-level sections."""
    summary = {
        "generatedAt": "2026-02-26T00:00:00Z",
        "riskTier": {"label": "high"},
        "counts": {"risks": 1, "controls": 1, "practices": 1, "recommendedTools": 1},
        "risks": [{"id": "R1", "title": "Prompt Injection", "category": "Runtime Input Security", "summary": "desc"}],
        "controls": [{
            "id": "C1",
            "title": "Input Validation",
            "category": "Application",
            "summary": "control desc",
            "mitigatesRiskTitles": ["Prompt Injection"],
        }],
        "practices": [{
            "title": "Input Validation",
            "practice": "Validate prompts.",
            "ownerRoles": ["Model Creator"],
            "lifecycleStages": ["runtime"],
        }],
        "recommendedTools": [{
            "name": "OWASP Top 10 for LLM",
            "description": "tool desc",
            "mappedItems": ["LLM01"],
            "reference": "https://owasp.org",
        }],
    }

    markdown = summary_to_markdown(summary)

    assert "## Risks" in markdown
    assert "## Controls" in markdown
    assert "## Practices" in markdown
    assert "## Recommended Tools" in markdown
    assert "Prompt Injection" in markdown
    assert "OWASP Top 10 for LLM" in markdown
