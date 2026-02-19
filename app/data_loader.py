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
        self._ai_inventory_schema: Optional[Dict[str, Any]] = None
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
    
    def _merge_steps_by_id(self, steps: List[dict]) -> List[dict]:
        """Merge steps with duplicate IDs into a single step (combines sections, fields, etc.)."""
        by_id: Dict[str, dict] = {}
        order: List[str] = []

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

    @property
    def ai_inventory_schema(self) -> Dict[str, Any]:
        """Get AI inventory form schema, loading if necessary."""
        if self._ai_inventory_schema is None:
            try:
                schema = self.load_yaml("ai-inventory.yaml")
                steps = schema.get("steps", [])
                if steps:
                    schema = {**schema, "steps": self._merge_steps_by_id(steps)}
                self._ai_inventory_schema = schema
            except DataLoadError:
                self._ai_inventory_schema = {}
        return self._ai_inventory_schema

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

    # --- Vayu Assessment ---
    def get_vayu_config(self) -> Dict[str, Any]:
        """Get Vayu assessment config (tiers, useCases, questions, scoring)."""
        return self.self_assessment.get('vayuAssessment', {})

    def get_vayu_use_cases(self) -> Dict[str, Any]:
        """Get Vayu use case selection question."""
        return self.get_vayu_config().get('useCases', {})

    def get_vayu_questions(self) -> List[Dict[str, Any]]:
        """Get Vayu assessment questions."""
        return self.get_vayu_config().get('questions', [])

    def get_vayu_tiers(self) -> List[Dict[str, Any]]:
        """Get Vayu tier definitions."""
        return self.get_vayu_config().get('tiers', [])

    def calculate_vayu_tier(
        self,
        use_case_selections: List[str],
        answers: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Calculate Vayu tier from use case selections and question answers.
        Returns dict with tier, label, baselineTier, escalatedRules, and method.
        """
        config = self.get_vayu_config()
        if not config:
            return {'tier': 1, 'label': 'low', 'baselineTier': 1, 'escalatedRules': [], 'method': []}

        tiers = {t['label']: t['value'] for t in config.get('tiers', [])}
        scoring = config.get('scoring', {})
        baseline_cfg = scoring.get('baseline', {})
        escalation_rules = scoring.get('escalationRules', [])
        questions_by_id = {q['id']: q for q in self.get_vayu_questions()}
        q_by_driver = {q.get('driver'): q['id'] for q in questions_by_id.values() if q.get('driver')}
        q_by_control = {q.get('control'): q['id'] for q in questions_by_id.values() if q.get('control')}

        def _answer_matches(ans: Any, in_answers: List[Any]) -> bool:
            """Match answer to in_answers (handles YAML Yes/No -> True/False)."""
            if ans is None:
                return False
            normalized = list(in_answers) if in_answers else []
            if True in normalized and "Yes" not in normalized:
                normalized.append("Yes")
            if False in normalized and "No" not in normalized:
                normalized.append("No")
            return ans in normalized

        # 1. Use case baseline
        default_tier = baseline_cfg.get('defaultTier', 'low')
        baseline_value = tiers.get(default_tier, 1)
        if use_case_selections:
            for ans in self.get_vayu_use_cases().get('answers', []):
                if ans.get('label') in use_case_selections and 'baselineTier' in ans:
                    tval = tiers.get(ans['baselineTier'], 1)
                    baseline_value = max(baseline_value, tval)

        # 2. Baseline gates
        gate_order = baseline_cfg.get('gateOrder', [])
        for gate_id in gate_order:
            q = questions_by_id.get(gate_id)
            if not q:
                continue
            q_id = q['id']
            if q_id not in answers:
                continue
            gate = q.get('baselineGate', {})
            if _answer_matches(answers.get(q_id), gate.get('if_answer_in', [])):
                then_tier = gate.get('then_tier', 'low')
                baseline_value = max(baseline_value, tiers.get(then_tier, 1))

        final_value = baseline_value
        escalated_rules = []

        # 3. Escalation rules
        for rule in escalation_rules:
            when = rule.get('when', {})
            then = rule.get('then', {})
            min_tier = tiers.get(then.get('set_minimum_tier', 'low'), 1)

            if 'all' in when:
                all_ok = True
                for cond in when['all']:
                    if 'driver' in cond:
                        q_id = q_by_driver.get(cond['driver'])
                    elif 'control' in cond:
                        q_id = q_by_control.get(cond['control'])
                    else:
                        all_ok = False
                        break
                    if not q_id or not _answer_matches(answers.get(q_id), cond.get('in_answers', [])):
                        all_ok = False
                        break
                if all_ok:
                    final_value = max(final_value, min_tier)
                    escalated_rules.append(rule.get('text', rule.get('id', '')))
            elif 'any' in when:
                any_ok = False
                for cond in when['any']:
                    if 'driver' in cond:
                        q_id = q_by_driver.get(cond['driver'])
                    elif 'control' in cond:
                        q_id = q_by_control.get(cond['control'])
                    else:
                        continue
                    if q_id and _answer_matches(answers.get(q_id), cond.get('in_answers', [])):
                        any_ok = True
                        break
                if any_ok:
                    final_value = max(final_value, min_tier)
                    escalated_rules.append(rule.get('text', rule.get('id', '')))

        label = next((t['label'] for t in config.get('tiers', []) if t['value'] == final_value), 'low')
        return {
            'tier': final_value,
            'label': label,
            'baselineTier': baseline_value,
            'escalatedRules': escalated_rules,
            'method': config.get('scoring', {}).get('finalTier', {}).get('method', []),
        }
    
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
