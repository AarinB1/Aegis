# triage_engine.py - Person 3 (Ansh) - Enhanced SALT/TCCC Triage Engine with LLM
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

# Import from team's shared modules
from shared.state import app_state
from schema import Casualty, AISuggestion, TriageCategory, Intervention, Wound

# Import LLM integration with fallback
try:
    from llm_integration import OllamaTriageAnalyzer
    LLM_AVAILABLE = True
except ImportError:
    print("LLM integration not available - running in rule-based mode")
    LLM_AVAILABLE = False
    class OllamaTriageAnalyzer:
        def __init__(self):
            self.available = False
        def enhance_triage_reasoning(self, evidence, scores, rule_priority):
            return {
                'priority': rule_priority,
                'confidence': 0.8,
                'reasoning': ['Rule-based analysis (LLM unavailable)'],
                'source': 'rule_based_fallback'
            }

class TriageEngine:
    """Enhanced SALT/TCCC rule-based triage engine with LLM reasoning"""

    def __init__(self, db_path="mascal.db"):
        self.db_path = db_path
        self.init_database()
        self.llm_analyzer = OllamaTriageAnalyzer()
        self.severity_map = {"minor": 0.3, "moderate": 0.6, "severe": 0.9}

    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS casualty_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    casualty_id TEXT, timestamp TEXT, data TEXT, source TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS triage_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    casualty_id TEXT, suggested_priority TEXT, confidence REAL,
                    reasoning TEXT, evidence TEXT, timestamp TEXT,
                    confirmed BOOLEAN DEFAULT FALSE, llm_enhanced BOOLEAN DEFAULT FALSE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    casualty_id TEXT, intervention_type TEXT, location TEXT,
                    timestamp TEXT, notes TEXT
                )
            """)

    def process_all_casualties(self):
        try:
            casualties = app_state.get_roster()
            pending = app_state.get_pending_suggestions()
            for casualty in casualties:
                if any(s.casualty_id == casualty.casualty_id for s in pending):
                    continue
                suggestion = self.analyze_casualty(casualty)
                if suggestion:
                    app_state.add_suggestion(suggestion)
                    self.log_triage_decision(suggestion)
        except Exception as e:
            app_state.audit("triage_engine", "error", {"message": str(e)})

    def analyze_casualty(self, casualty: Casualty) -> Optional[AISuggestion]:
        try:
            evidence = self.gather_evidence(casualty)
            scores = self.calculate_triage_scores(evidence)
            rule_priority = self.determine_priority(scores)
            llm_result = self.llm_analyzer.enhance_triage_reasoning(
                evidence, scores, rule_priority.value
            )
            suggestion = AISuggestion(
                timestamp=datetime.now(),
                source="triage_engine_llm",
                suggestion=f"Suggested triage: {llm_result['priority']} priority - {'; '.join(llm_result['reasoning'][:2])}",
                confidence=llm_result['confidence']
            )
            casualty.ai_suggestions_log.append(suggestion)
            app_state.upsert_casualty(casualty)
            return suggestion
        except Exception as e:
            app_state.audit("triage_engine", "analysis_error",
                {"casualty_id": casualty.casualty_id, "error": str(e)})
            return None

    def gather_evidence(self, casualty: Casualty) -> Dict:
        evidence = {
            'casualty_id': casualty.casualty_id,
            'wounds': [],
            'vitals': {
                'respiratory_status': casualty.respiratory_status.value if casualty.respiratory_status else 'unknown',
                'respiratory_rate': casualty.respiratory_rate,
                'responsive': casualty.responsive
            },
            'audio_findings': [],
            'interventions': [],
            'timestamp': datetime.now().isoformat()
        }
        for wound in casualty.wounds:
            evidence['wounds'].append({
                'type': 'laceration',
                'severity': self.severity_map.get(wound.severity, 0.5),
                'bleeding': wound.active_bleeding,
                'location': wound.location,
                'area_cm2': wound.area_cm2,
                'confidence': wound.ai_confidence
            })
        try:
            audio_sugg = [s for s in app_state.get_pending_suggestions()
                         if s.casualty_id == casualty.casualty_id and s.source == "audio"]
            for s in audio_sugg:
                text = s.raw.suggestion if hasattr(s, 'raw') and hasattr(s.raw, 'suggestion') else str(s)
                if "AIRWAY COMPROMISE" in text:
                    classification = "AIRWAY COMPROMISE"
                elif "NORMAL" in text:
                    classification = "NORMAL"
                else:
                    classification = "UNKNOWN"
                evidence['audio_findings'].append({
                    'classification': classification,
                    'confidence': s.confidence,
                    'details': text
                })
        except Exception:
            pass
        for intervention in casualty.interventions:
            evidence['interventions'].append({
                'type': intervention.type,
                'location': intervention.location,
                'timestamp': intervention.timestamp.isoformat(),
                'source': intervention.source
            })
        return evidence

    def calculate_triage_scores(self, evidence: Dict) -> Dict:
        scores = {'wound_score': 0, 'bleeding_score': 0, 'respiratory_score': 0,
                  'location_score': 0, 'consciousness_score': 5, 'total_score': 0}
        for wound in evidence['wounds']:
            scores['wound_score'] += wound['severity'] * 10
            if wound['bleeding']:
                scores['bleeding_score'] += 15
            loc = wound['location'].lower()
            if any(x in loc for x in ['head', 'neck', 'skull']):
                scores['location_score'] += 20
            elif any(x in loc for x in ['chest', 'torso', 'abdomen']):
                scores['location_score'] += 15
            elif any(x in loc for x in ['thigh', 'arm', 'leg', 'limb']):
                scores['location_score'] += 5
            scores['wound_score'] += min(wound.get('area_cm2', 0) / 10, 5)
        for finding in evidence['audio_findings']:
            cls = finding.get('classification', '').upper()
            conf = finding.get('confidence', 0.5)
            if 'AIRWAY COMPROMISE' in cls:
                scores['respiratory_score'] += 25 * conf
            elif 'DISTRESS' in cls:
                scores['respiratory_score'] += 20 * conf
            elif 'ABNORMAL' in cls:
                scores['respiratory_score'] += 10 * conf
        vitals = evidence.get('vitals', {})
        if vitals.get('respiratory_rate'):
            rr = vitals['respiratory_rate']
            if rr > 30 or rr < 10:
                scores['respiratory_score'] += 15
            elif rr > 24 or rr < 12:
                scores['respiratory_score'] += 5
        if vitals.get('responsive') is False:
            scores['consciousness_score'] = 0
        scores['total_score'] = (
            scores['wound_score'] * 1.0 + scores['bleeding_score'] * 1.5 +
            scores['respiratory_score'] * 1.4 + scores['location_score'] * 1.3 +
            max(0, 10 - scores['consciousness_score']) * 2.0
        )
        return scores

    def determine_priority(self, scores: Dict) -> TriageCategory:
        total = scores['total_score']
        if (total >= 50 or scores['bleeding_score'] >= 20 or
            scores['respiratory_score'] >= 25 or scores['location_score'] >= 20):
            return TriageCategory.IMMEDIATE
        if (total >= 25 or scores['bleeding_score'] >= 10 or
            scores['respiratory_score'] >= 15 or scores['wound_score'] >= 20):
            return TriageCategory.DELAYED
        return TriageCategory.MINIMAL

    def generate_medevac_9_line(self, casualty_id: str) -> Dict:
        casualty = app_state.get_casualty(casualty_id)
        if not casualty:
            return {}
        nine_line = {
            'line_1_location': f'GRID {self.get_gps_coordinates(casualty_id)}',
            'line_2_radio_freq': '142.375 MHz',
            'line_3_patients_by_priority': self.get_patient_priority_counts(),
            'line_4_special_equipment': self.determine_special_equipment(casualty),
            'line_5_patients_by_type': 'LITTER: 1',
            'line_6_security': 'NO ENEMY TROOPS IN AREA',
            'line_7_marking': 'GREEN SMOKE SIGNAL',
            'line_8_patient_nationality': 'US MILITARY',
            'line_9_nbc_contamination': 'NONE',
            'generated_time': datetime.now().isoformat(),
            'casualty_id': casualty_id,
            'priority_justification': self.get_medevac_justification(casualty_id)
        }
        app_state.set_active_medevac(casualty_id, nine_line)
        self.log_medevac_request(casualty_id, nine_line)
        return nine_line

    def determine_special_equipment(self, casualty: Casualty) -> str:
        equipment = []
        for wound in casualty.wounds:
            if wound.active_bleeding:
                equipment.append('BLOOD PRODUCTS')
            if any(x in wound.location.lower() for x in ['head', 'neck']):
                equipment.append('AIRWAY MANAGEMENT')
            if wound.severity == "severe":
                equipment.append('SURGICAL CAPABILITY')
        return ', '.join(equipment) if equipment else 'NONE'

    def get_patient_priority_counts(self) -> str:
        casualties = app_state.get_roster()
        counts = {'red': 0, 'yellow': 0, 'green': 0, 'gray': 0}
        for c in casualties:
            cat = c.triage_category.value
            counts[cat] = counts.get(cat, 0) + 1
        return f"RED: {counts['red']}, YELLOW: {counts['yellow']}, GREEN: {counts['green']}"

    def get_gps_coordinates(self, casualty_id: str) -> str:
        return "TBD - AWAITING GPS"

    def get_medevac_justification(self, casualty_id: str) -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    SELECT suggested_priority, reasoning FROM triage_decisions
                    WHERE casualty_id = ? ORDER BY timestamp DESC LIMIT 1
                """, (casualty_id,))
                result = cur.fetchone()
                if result:
                    priority, reasoning_json = result
                    reasoning = json.loads(reasoning_json)
                    return f"{priority} PRIORITY: {'; '.join(reasoning[:2])}"
        except Exception as e:
            print(f"Error getting justification: {e}")
        return "MEDICAL EVACUATION REQUIRED"

    def log_triage_decision(self, suggestion: AISuggestion):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO triage_decisions
                    (casualty_id, suggested_priority, confidence, reasoning,
                     evidence, timestamp, llm_enhanced)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ('unknown', suggestion.suggestion, suggestion.confidence,
                      json.dumps([suggestion.suggestion]), json.dumps({}),
                      suggestion.timestamp.isoformat(), LLM_AVAILABLE))
        except Exception as e:
            print(f"Failed to log: {e}")

    def log_medevac_request(self, casualty_id: str, nine_line: Dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO casualty_history (casualty_id, timestamp, data, source)
                VALUES (?, ?, ?, ?)
            """, (casualty_id, datetime.now().isoformat(),
                  json.dumps(nine_line), 'medevac_request'))


def start_triage_engine():
    engine = TriageEngine()
    print("Triage Engine initialized")
    print(f"LLM: {'Available' if LLM_AVAILABLE and engine.llm_analyzer.available else 'Unavailable'}")
    return engine


__all__ = ['TriageEngine', 'start_triage_engine']
