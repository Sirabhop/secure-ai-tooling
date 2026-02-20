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
        self._routing: Optional[Dict[str, Any]] = None
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

    @property
    def routing(self) -> Dict[str, Any]:
        """Get routing config, loading if necessary."""
        if self._routing is None:
            try:
                self._routing = self.load_yaml("routing.yaml")
            except DataLoadError:
                self._routing = {}
        return self._routing

    # ── Routing engine ────────────────────────────────────────────────────

    def _eval_routing_predicate(self, pred: dict, row: Dict[str, Any]) -> bool:
        """Evaluate a predicate against a single data row (handles nesting)."""
        if "all" in pred:
            return all(self._eval_routing_predicate(p, row) for p in pred["all"])
        if "any" in pred:
            return any(self._eval_routing_predicate(p, row) for p in pred["any"])

        field = pred.get("field", "")
        value = row.get(field)

        if "exists" in pred:
            return (value is not None and value != "" and value != []) == pred["exists"]
        if "equals" in pred:
            return value == pred["equals"]
        if "notEquals" in pred:
            return value != pred["notEquals"]
        if "in" in pred:
            return value in pred["in"]
        if "includes" in pred:
            return (pred["includes"] in value) if isinstance(value, list) else value == pred["includes"]
        if "includesAny" in pred:
            targets = pred["includesAny"]
            return any(t in value for t in targets) if isinstance(value, list) else value in targets
        return False

    def _eval_routing_condition(
        self, cond: dict, data: Dict[str, Any], flags: Dict[str, Any], repeat_blocks: Dict[str, list],
    ) -> bool:
        """Evaluate a single top-level routing condition (field, flag, fact, repeatAny, repeatAllIfPresent)."""
        if "field" in cond:
            return self._eval_routing_predicate(cond, data)

        if "flag" in cond:
            flag_val = flags.get(cond["flag"])
            if "equals" in cond:
                return flag_val == cond["equals"]
            return False

        if "fact" in cond:
            fact_val = flags.get(cond["fact"])
            if "equals" in cond:
                return fact_val == cond["equals"]
            if "in" in cond:
                return fact_val in cond["in"]
            return False

        if "repeatAny" in cond:
            ra = cond["repeatAny"]
            rows = repeat_blocks.get(ra.get("blockId", ""), [])
            predicate = ra.get("predicate", {})
            return any(self._eval_routing_predicate(predicate, r) for r in rows)

        if "repeatAllIfPresent" in cond:
            raip = cond["repeatAllIfPresent"]
            rows = repeat_blocks.get(raip.get("blockId", ""), [])
            filter_pred = raip.get("predicate", {})
            must_satisfy = raip.get("allMustSatisfy", {})
            matching = [r for r in rows if self._eval_routing_predicate(filter_pred, r)]
            if not matching:
                return True
            return all(self._eval_routing_predicate(must_satisfy, r) for r in matching)

        return False

    def _eval_routing_when(
        self, when: dict, data: Dict[str, Any], flags: Dict[str, Any], repeat_blocks: Dict[str, list],
    ) -> bool:
        """Evaluate a when clause from routing.yaml factRules."""
        if not when:
            return False
        if "any" in when:
            return any(self._eval_routing_condition(c, data, flags, repeat_blocks) for c in when["any"])
        if "all" in when:
            return all(self._eval_routing_condition(c, data, flags, repeat_blocks) for c in when["all"])
        return False

    def _collect_when_fields(self, when: dict) -> set:
        """Recursively collect 'field' keys from a routing when condition."""
        out: set = set()
        if "field" in when:
            out.add(when["field"])
        for key in ("any", "all"):
            for c in when.get(key, []):
                out |= self._collect_when_fields(c)
        return out

    def _get_field_label(self, field_key: str) -> str:
        """Resolve inventory field key to human-readable label from schema."""
        schema = self.ai_inventory_schema
        for step in schema.get("steps", []):
            for f in step.get("fields", []):
                if f.get("key") == field_key:
                    return f.get("label", field_key)
            for sec in step.get("sections", []):
                for f in sec.get("fields", []):
                    if f.get("key") == field_key:
                        return f.get("label", field_key)
        return field_key

    def _get_fact_origin(
        self, fact_name: str, fact_value: Any, inventory_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Trace a fact value back to the inventory field(s) that drove it."""
        if not inventory_data:
            return ""
        routing = self.routing
        rules = routing.get("factRules", [])
        fields_used: set = set()
        for rule in rules:
            set_facts = rule.get("setFacts", {})
            if fact_name not in set_facts:
                continue
            fields_used |= self._collect_when_fields(rule.get("when", {}))
        if not fields_used:
            return ""
        parts = []
        for fk in sorted(fields_used):
            val = inventory_data.get(fk)
            if val is None or val == "":
                continue
            label = self._get_field_label(fk)
            if isinstance(val, list):
                val = ", ".join(str(x) for x in val)
            parts.append(f"{label} = \"{val}\"")
        return " → ".join(parts) if parts else ""

    def _format_when_reason(
        self, when: dict, facts: Dict[str, Any], inventory_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format a 'when' condition into a short human-readable reason string.
        For fact-based conditions, traces back to inventory field(s) when possible.
        """
        parts: List[str] = []
        if "field" in when:
            f = when["field"]
            v = inventory_data.get(f) if inventory_data else None
            label = self._get_field_label(f) if inventory_data else f
            if "equals" in when:
                parts.append(f"{label} = \"{when['equals']}\"")
            elif "in" in when:
                parts.append(f"{label} in {when['in']}")
            elif "exists" in when:
                parts.append(f"{label} exists = {when['exists']}")
            else:
                parts.append(f"{label} = \"{v}\"")
        elif "fact" in when:
            f = when["fact"]
            v = facts.get(f)
            origin = self._get_fact_origin(f, v, inventory_data)
            if origin:
                return origin
            if "equals" in when:
                parts.append(f"{f} = {when['equals']}")
            elif "in" in when:
                parts.append(f"{f} in {when['in']}")
            else:
                parts.append(f"{f} = {v}")
        elif "any" in when:
            for c in when["any"][:2]:  # max 2 for brevity
                parts.append(self._format_when_reason(c, facts, inventory_data))
            if len(when["any"]) > 2:
                parts.append("...")
            return " OR ".join(parts)
        elif "all" in when:
            for c in when["all"][:2]:
                parts.append(self._format_when_reason(c, facts, inventory_data))
            if len(when["all"]) > 2:
                parts.append("...")
            return " AND ".join(parts)
        return " OR ".join(parts) if parts else "—"

    def _eval_question_condition(
        self, when: dict, facts: Dict[str, Any], inventory_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Evaluate a condition from questionRules (defaultAnswerFromFacts, visibleWhen, requiredWhen).

        Handles fact references (checked against computed facts) and field
        references (checked against inventory data).
        """
        if "fact" in when:
            val = facts.get(when["fact"])
            if "equals" in when:
                return val == when["equals"]
            if "in" in when:
                return val in when["in"]
            return False
        if "field" in when:
            inv = inventory_data or {}
            val = inv.get(when["field"])
            if "exists" in when:
                return (val is not None and val != "" and val != []) == when["exists"]
            if "equals" in when:
                return val == when["equals"]
            if "in" in when:
                return val in when["in"]
            if "includes" in when:
                return (when["includes"] in val) if isinstance(val, list) else val == when["includes"]
            return False
        if "any" in when:
            return any(self._eval_question_condition(c, facts, inventory_data) for c in when["any"])
        if "all" in when:
            return all(self._eval_question_condition(c, facts, inventory_data) for c in when["all"])
        return False

    def compute_inventory_flags(self, inventory_data: Dict[str, Any], repeat_blocks: Dict[str, list]) -> Dict[str, Any]:
        """Recompute AI inventory flags from schema rules."""
        schema = self.ai_inventory_schema
        flags: Dict[str, Any] = dict(schema.get("flags", {}).get("defaults", {}))
        for rule in schema.get("rules", []):
            when = rule.get("when")
            set_flags = rule.get("setFlags")
            if not set_flags or not when:
                continue
            if self._eval_routing_when(when, inventory_data, {}, repeat_blocks):
                flags.update(set_flags)
        return flags

    def compute_routing_facts(self, inventory_data: Dict[str, Any], repeat_blocks: Dict[str, list]) -> Dict[str, Any]:
        """Compute routing facts from inventory data → inventory flags → factRules.

        Rules are evaluated top-to-bottom. Later rules can reference facts set
        by earlier rules via ``fact:`` conditions because previously computed
        facts are merged into the flags context on each iteration.
        """
        inv_flags = self.compute_inventory_flags(inventory_data, repeat_blocks)
        routing = self.routing
        facts: Dict[str, Any] = dict(routing.get("facts", {}).get("defaults", {}))
        for rule in routing.get("factRules", []):
            when = rule.get("when", {})
            set_facts = rule.get("setFacts", {})
            if not set_facts:
                continue
            merged_flags = {**inv_flags, **facts}
            if self._eval_routing_when(when, inventory_data, merged_flags, repeat_blocks):
                facts.update(set_facts)
        return facts

    def get_prefilled_assessment_data(
        self, inventory_data: Dict[str, Any], repeat_blocks: Dict[str, list],
    ) -> Dict[str, Any]:
        """Compute all prefill data for assessments from inventory.

        Returns dict with:
          facts, prefilled_answers, prefilled_use_cases, prefilled_personas,
          hidden_questions (set of question IDs whose visibleWhen evaluated to False).
        """
        empty = {
            "facts": {}, "prefilled_answers": {}, "prefilled_use_cases": [],
            "prefilled_personas": [], "hidden_questions": set(),
            "prefill_reasons": {"use_cases": {}, "personas": {}, "answers": {}},
        }
        if not inventory_data:
            return empty

        facts = self.compute_routing_facts(inventory_data, repeat_blocks)
        logger.info("Computed routing facts: %d active", sum(1 for v in facts.values() if v))
        routing = self.routing

        prefilled_answers: Dict[str, str] = {}
        prefilled_use_cases: List[str] = []
        prefilled_personas: List[str] = []
        hidden_questions: set = set()
        use_case_reasons: Dict[str, str] = {}
        persona_reasons: Dict[str, str] = {}
        answer_reasons: Dict[str, str] = {}

        for route in routing.get("assessmentRouting", []):
            # Use case prefill
            uc_cfg = route.get("prefill", {}).get("useCases", {})
            if uc_cfg:
                source_field = uc_cfg.get("sourceField", "")
                source_val = inventory_data.get(source_field)
                mapped = uc_cfg.get("mapping", {}).get(source_val)
                if mapped:
                    prefilled_use_cases.append(mapped)
                    use_case_reasons[mapped] = f"{source_field} = \"{source_val}\""

            # Persona prefill
            for pid, pcond in route.get("personas", {}).items():
                fact_key = pcond.get("fact", "")
                if fact_key and facts.get(fact_key) == pcond.get("equals"):
                    prefilled_personas.append(pid)
                    # Persona facts derive from modelCreator; show that chain
                    model_val = inventory_data.get("modelCreator")
                    persona_reasons[pid] = f"modelCreator = \"{model_val}\""

            # Question rules: visibility + answer prefill
            for qr in route.get("questionRules", []):
                q_id = qr.get("questionId")

                # Visibility check
                vis_when = qr.get("visibleWhen")
                if vis_when and not self._eval_question_condition(vis_when, facts, inventory_data):
                    hidden_questions.add(q_id)
                    continue

                # Answer prefill
                for d in qr.get("defaultAnswerFromFacts", []):
                    when = d.get("when", {})
                    if self._eval_question_condition(when, facts, inventory_data):
                        answer = d.get("answer")
                        if answer is True:
                            prefilled_answers[q_id] = "Yes"
                        elif answer is False:
                            prefilled_answers[q_id] = "No"
                        else:
                            prefilled_answers[q_id] = str(answer)
                        answer_reasons[q_id] = self._format_when_reason(when, facts, inventory_data)
                        break

        result = {
            "facts": facts,
            "prefilled_answers": prefilled_answers,
            "prefilled_use_cases": prefilled_use_cases,
            "prefilled_personas": prefilled_personas,
            "hidden_questions": hidden_questions,
            "prefill_reasons": {
                "use_cases": use_case_reasons,
                "personas": persona_reasons,
                "answers": answer_reasons,
            },
        }
        logger.info(
            "Prefill from inventory: personas=%s, use_cases=%s, answers=%d, hidden=%d",
            prefilled_personas, prefilled_use_cases, len(prefilled_answers), len(hidden_questions),
        )
        return result

    def has_load_errors(self) -> bool:
        """Check if there were any errors during data loading."""
        return bool(self._load_errors)
    
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
        result = {
            'tier': final_value,
            'label': label,
            'baselineTier': baseline_value,
            'escalatedRules': escalated_rules,
            'method': config.get('scoring', {}).get('finalTier', {}).get('method', []),
        }
        logger.info("Vayu tier: %s (baseline=%s, escalated=%d)", label, baseline_value, len(escalated_rules))
        return result

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

        result = sorted(relevant_risks)
        logger.info("Relevant risks: %d risks for personas=%s -> %s", len(result), selected_personas, result[:10])
        return result
    
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
    
    # ── Mock prefill scenarios ─────────────────────────────────────────────

    def load_mock_prefills(self) -> List[Dict[str, Any]]:
        """Load mock prefill scenarios from mock-prefills.yaml."""
        try:
            data = self.load_yaml("mock-prefills.yaml")
            scenarios = data.get("scenarios", [])
            logger.info("Loaded %d mock prefill scenarios: %s", len(scenarios), [s.get("id") for s in scenarios])
            return scenarios
        except DataLoadError:
            logger.warning("Mock prefills not available (mock-prefills.yaml)")
            return []

    @staticmethod
    def flatten_inventory_scenario(scenario: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, list]]:
        """Flatten a mock scenario's inventory into (flat_data, repeat_blocks).

        The UI stores all non-repeating fields in a single flat dict keyed by
        field ``key`` and repeating-block rows under separate session-state keys.
        """
        inv = scenario.get("inventory", {})
        flat: Dict[str, Any] = {}
        repeat_blocks: Dict[str, list] = {}

        for step_key, step_val in inv.items():
            if step_val is None:
                continue
            if isinstance(step_val, dict):
                # Repeating blocks (step4.models, step6.dataSources)
                for k, v in step_val.items():
                    if k == "models":
                        repeat_blocks["block4Models"] = list(v) if isinstance(v, list) else []
                    elif k == "dataSources":
                        repeat_blocks["block6DataSources"] = list(v) if isinstance(v, list) else []
                    elif isinstance(v, dict):
                        # Nested section (sec2a, sec3b, etc.)
                        flat.update(v)
                    else:
                        flat[k] = v
            else:
                flat[step_key] = step_val

        return flat, repeat_blocks

    def get_risk_details(self, risk_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a risk."""
        return self.risks.get(risk_id)
    
    def get_control_details(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a control."""
        return self.controls.get(control_id)
