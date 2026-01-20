"""Data loader for CoSAI Risk Map YAML files."""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class RiskMapDataLoader:
    """Loads and processes CoSAI Risk Map YAML data."""
    
    def __init__(self, yaml_dir: str = None):
        if yaml_dir is None:
            # Default to risk-map/yaml relative to project root
            project_root = Path(__file__).parent.parent
            self.yaml_dir = project_root / "risk-map" / "yaml"
        else:
            self.yaml_dir = Path(yaml_dir)
        self._risks: Optional[Dict[str, Any]] = None
        self._controls: Optional[Dict[str, Any]] = None
        self._self_assessment: Optional[Dict[str, Any]] = None
        self._personas: Optional[Dict[str, Any]] = None
        
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML file."""
        filepath = self.yaml_dir / filename
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @property
    def risks(self) -> Dict[str, Any]:
        """Get risks data, loading if necessary."""
        if self._risks is None:
            data = self.load_yaml("risks.yaml")
            self._risks = {risk['id']: risk for risk in data.get('risks', [])}
        return self._risks
    
    @property
    def controls(self) -> Dict[str, Any]:
        """Get controls data, loading if necessary."""
        if self._controls is None:
            data = self.load_yaml("controls.yaml")
            self._controls = {control['id']: control for control in data.get('controls', [])}
        return self._controls
    
    @property
    def self_assessment(self) -> Dict[str, Any]:
        """Get self-assessment data, loading if necessary."""
        if self._self_assessment is None:
            self._self_assessment = self.load_yaml("self-assessment.yaml")
        return self._self_assessment
    
    @property
    def personas(self) -> Dict[str, Any]:
        """Get personas data, loading if necessary."""
        if self._personas is None:
            data = self.load_yaml("personas.yaml")
            self._personas = {p['id']: p for p in data.get('personas', [])}
        return self._personas
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """Get assessment questions."""
        return self.self_assessment.get('selfAssessment', {}).get('questions', [])
    
    def get_persona_question(self) -> Dict[str, Any]:
        """Get persona selection question."""
        return self.self_assessment.get('selfAssessment', {}).get('personas', {})
    
    def calculate_relevant_risks(self, answers: Dict[str, str], selected_personas: List[str]) -> List[str]:
        """Calculate which risks are relevant based on answers."""
        relevant_risks = set()
        questions = self.get_questions()
        
        for question in questions:
            q_id = question['id']
            if q_id not in answers:
                continue
            
            # Check if question applies to selected personas
            question_personas = question.get('personas', [])
            if not any(p in selected_personas for p in question_personas):
                continue
            
            answer_label = answers[q_id]
            relevance = question.get('relevance', [])
            
            # If answer matches relevance criteria, add associated risks
            if answer_label in relevance:
                risks = question.get('risks', [])
                relevant_risks.update(risks)
        
        return sorted(list(relevant_risks))
    
    def get_controls_for_risks(self, risk_ids: List[str]) -> List[Dict[str, Any]]:
        """Get all controls that address the given risks."""
        controls_set = set()
        controls_data = []
        
        for risk_id in risk_ids:
            risk = self.risks.get(risk_id)
            if risk:
                risk_controls = risk.get('controls', [])
                for control_id in risk_controls:
                    if control_id not in controls_set:
                        controls_set.add(control_id)
                        control = self.controls.get(control_id)
                        if control:
                            controls_data.append(control)
        
        return controls_data
    
    def format_text_list(self, text_list: List[str]) -> str:
        """Format a list of text items into a single string."""
        if not text_list:
            return ""
        return " ".join(text_list)
    
    def get_risk_details(self, risk_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a risk."""
        return self.risks.get(risk_id)
    
    def get_control_details(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a control."""
        return self.controls.get(control_id)
