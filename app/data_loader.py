"""Data loader for CoSAI Risk Map YAML files."""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Custom exception for data loading errors."""
    pass


class RiskMapDataLoader:
    """Loads and processes CoSAI Risk Map YAML data."""
    
    def __init__(self, yaml_dir: str = None):
        if yaml_dir is None:
            # Default to risk-map/yaml relative to project root
            project_root = Path(__file__).parent.parent
            self.yaml_dir = project_root / "risk-map" / "yaml"
        else:
            self.yaml_dir = Path(yaml_dir)
        
        # Validate directory exists
        if not self.yaml_dir.exists():
            raise DataLoadError(f"YAML directory not found: {self.yaml_dir}")
        
        self._risks: Optional[Dict[str, Any]] = None
        self._controls: Optional[Dict[str, Any]] = None
        self._self_assessment: Optional[Dict[str, Any]] = None
        self._personas: Optional[Dict[str, Any]] = None
        self._load_errors: Dict[str, str] = {}
        
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML file with error handling."""
        filepath = self.yaml_dir / filename
        
        if not filepath.exists():
            error_msg = f"File not found: {filepath}"
            logger.error(error_msg)
            self._load_errors[filename] = error_msg
            raise DataLoadError(error_msg)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data is None:
                    error_msg = f"Empty or invalid YAML file: {filename}"
                    logger.warning(error_msg)
                    self._load_errors[filename] = error_msg
                    return {}
                return data
        except yaml.YAMLError as e:
            error_msg = f"YAML parsing error in {filename}: {str(e)}"
            logger.error(error_msg)
            self._load_errors[filename] = error_msg
            raise DataLoadError(error_msg) from e
        except Exception as e:
            error_msg = f"Error loading {filename}: {str(e)}"
            logger.error(error_msg)
            self._load_errors[filename] = error_msg
            raise DataLoadError(error_msg) from e
    
    @property
    def risks(self) -> Dict[str, Any]:
        """Get risks data, loading if necessary."""
        if self._risks is None:
            try:
                data = self.load_yaml("risks.yaml")
                risks_list = data.get('risks', [])
                if not risks_list:
                    logger.warning("No risks found in risks.yaml")
                    self._risks = {}
                else:
                    self._risks = {risk['id']: risk for risk in risks_list if 'id' in risk}
            except DataLoadError:
                self._risks = {}
        return self._risks
    
    @property
    def controls(self) -> Dict[str, Any]:
        """Get controls data, loading if necessary."""
        if self._controls is None:
            try:
                data = self.load_yaml("controls.yaml")
                controls_list = data.get('controls', [])
                if not controls_list:
                    logger.warning("No controls found in controls.yaml")
                    self._controls = {}
                else:
                    self._controls = {control['id']: control for control in controls_list if 'id' in control}
            except DataLoadError:
                self._controls = {}
        return self._controls
    
    @property
    def self_assessment(self) -> Dict[str, Any]:
        """Get self-assessment data, loading if necessary."""
        if self._self_assessment is None:
            try:
                self._self_assessment = self.load_yaml("self-assessment.yaml")
            except DataLoadError:
                self._self_assessment = {}
        return self._self_assessment
    
    @property
    def personas(self) -> Dict[str, Any]:
        """Get personas data, loading if necessary."""
        if self._personas is None:
            try:
                data = self.load_yaml("personas.yaml")
                personas_list = data.get('personas', [])
                if not personas_list:
                    logger.warning("No personas found in personas.yaml")
                    self._personas = {}
                else:
                    self._personas = {p['id']: p for p in personas_list if 'id' in p}
            except DataLoadError:
                self._personas = {}
        return self._personas
    
    def has_load_errors(self) -> bool:
        """Check if there were any errors during data loading."""
        return len(self._load_errors) > 0
    
    def get_load_errors(self) -> Dict[str, str]:
        """Get dictionary of load errors."""
        return self._load_errors.copy()
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """Get assessment questions."""
        return self.self_assessment.get('selfAssessment', {}).get('questions', [])
    
    def get_persona_question(self) -> Dict[str, Any]:
        """Get persona selection question."""
        return self.self_assessment.get('selfAssessment', {}).get('personas', {})
    
    def calculate_relevant_risks(self, answers: Dict[str, str], selected_personas: List[str]) -> List[str]:
        """Calculate which risks are relevant based on answers."""
        if not answers or not selected_personas:
            return []
        
        relevant_risks = set()
        questions = self.get_questions()
        
        if not questions:
            logger.warning("No questions available for risk calculation")
            return []
        
        for question in questions:
            q_id = question.get('id')
            if not q_id or q_id not in answers:
                continue
            
            # Check if question applies to selected personas
            question_personas = question.get('personas', [])
            if question_personas and not any(p in selected_personas for p in question_personas):
                continue
            
            answer_label = answers[q_id]
            relevance = question.get('relevance', [])
            
            # If answer matches relevance criteria, add associated risks
            if relevance and answer_label in relevance:
                risks = question.get('risks', [])
                if risks:
                    relevant_risks.update(risks)
        
        return sorted(list(relevant_risks))
    
    def get_controls_for_risks(self, risk_ids: List[str]) -> List[Dict[str, Any]]:
        """Get all controls that address the given risks."""
        if not risk_ids:
            return []
        
        controls_set = set()
        controls_data = []
        
        for risk_id in risk_ids:
            risk = self.risks.get(risk_id)
            if risk:
                risk_controls = risk.get('controls', [])
                for control_id in risk_controls:
                    if control_id and control_id not in controls_set:
                        controls_set.add(control_id)
                        control = self.controls.get(control_id)
                        if control:
                            controls_data.append(control)
        
        return controls_data
    
    def format_text_list(self, text_list: List[str]) -> str:
        """Format a list of text items into a single string."""
        if not text_list:
            return ""
        # Filter out None values and join with spaces
        return " ".join(str(item) for item in text_list if item)
    
    def get_risk_details(self, risk_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a risk."""
        return self.risks.get(risk_id)
    
    def get_control_details(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a control."""
        return self.controls.get(control_id)
