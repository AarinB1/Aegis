# triage_engine.py - Person 3 (Ansh) - Enhanced SALT/TCCC Triage Engine with LLM
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Import from team's shared modules (Aarin owns these)
try:
    from shared.state import app_state
    from schema import Casualty, Suggestion, TriageCategory, Intervention
except ImportError:
    print("⏳ Waiting for shared modules from Aarin (shared/state.py, schema.py)")
    # Create placeholder classes for testing
    class TriageCategory(Enum):
        RED = "RED"
        YELLOW = "YELLOW" 
        GREEN = "GREEN"
        BLACK = "BLACK"

# Import LLM integration
from llm_integration import OllamaTriageAnalyzer

class TriageEngine:
    """
    Enhanced SALT/TCCC rule-based triage engine with LLM reasoning
    - Processes evidence from Vision (Person 1) and Audio (Person 2)
    - Generates triage suggestions (never direct assignments)
    - Uses Ollama/Llama for enhanced medical reasoning
    - Applies medical protocols with conservative bias
    """
    
    def __init__(self, db_path="mascal.db"):
        self.db_path = db_path
        self.init_database()
        self.llm_analyzer = OllamaTriageAnalyzer()  # LLM integration
        
    def init_database(self):
        """Initialize SQLite database for persistence"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS casualty_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    casualty_id TEXT,
                    timestamp TEXT,
                    data TEXT,
                    source TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS triage_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    casualty_id TEXT,
                    suggested_priority TEXT,
                    confidence REAL,
                    reasoning TEXT,
                    evidence TEXT,
                    timestamp TEXT,
                    confirmed BOOLEAN DEFAULT FALSE,
                    llm_enhanced BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    casualty_id TEXT,
                    intervention_type TEXT,
                    location TEXT,
                    timestamp TEXT,
                    notes TEXT
                )
            """)
    
    def process_all_casualties(self):
        """
        Main processing loop - analyze all casualties and generate suggestions
        Called periodically by UI or event-driven
        """
        try:
            # Check if shared modules are available
            if 'app_state' not in globals():
                print("⏳ Waiting for AppState integration...")
                return
                
            casualties = app_state.get_roster()
            pending_suggestions = app_state.get_pending_suggestions()
            
            for casualty in casualties:
                # Skip if we already have pending suggestions for this casualty
                if any(s.casualty_id == casualty.id for s in pending_suggestions):
                    continue
                    
                suggestion = self.analyze_casualty(casualty)
                if suggestion:
                    app_state.add_suggestion(suggestion)
                    self.log_triage_decision(suggestion)
                    
        except Exception as e:
            if 'app_state' in globals():
                app_state.audit("triage_engine", "error", f"Processing failed: {str(e)}")
            else:
                print(f"Processing error: {e}")
    
    def analyze_casualty(self, casualty) -> Optional[dict]:
        """
        Enhanced analysis with Ollama integration
        Apply SALT/TCCC rules + LLM reasoning to generate triage suggestion
        """
        try:
            # Collect evidence
            evidence = self.gather_evidence(casualty)
            
            # Apply rule-based scoring algorithm
            scores = self.calculate_triage_scores(evidence)
            
            # Determine rule-based priority
            rule_priority = self.determine_priority(scores)
            
            # NEW: Enhance with LLM reasoning
            llm_result = self.llm_analyzer.enhance_triage_reasoning(
                evidence, scores, rule_priority.value if hasattr(rule_priority, 'value') else str(rule_priority)
            )
            
            # Create suggestion with LLM enhancement
            if 'app_state' in globals():
                suggestion = Suggestion(
                    casualty_id=casualty.id,
                    suggested_category=TriageCategory[llm_result['priority']],
                    confidence=llm_result['confidence'],
                    reasoning=llm_result['reasoning'],
                    source="triage_engine_llm",
                    supporting_evidence=evidence,
                    timestamp=datetime.now()
                )
            else:
                # Testing mode - return dict
                suggestion = {
                    'casualty_id': getattr(casualty, 'id', 'TEST_CASUALTY'),
                    'suggested_category': llm_result['priority'],
                    'confidence': llm_result['confidence'],
                    'reasoning': llm_result['reasoning'],
                    'source': 'triage_engine_llm',
                    'supporting_evidence': evidence,
                    'timestamp': datetime.now().isoformat(),
                    'llm_enhanced': True
                }
            
            return suggestion
            
        except Exception as e:
            error_msg = f"Failed to analyze casualty: {str(e)}"
            if 'app_state' in globals():
                app_state.audit("triage_engine", "analysis_error", error_msg)
            else:
                print(error_msg)
            return None
    
    def gather_evidence(self, casualty) -> Dict:
        """Collect all available evidence for this casualty"""
        evidence = {
            'casualty_id': getattr(casualty, 'id', 'TEST'),
            'wounds': [],
            'vitals': {},
            'audio_findings': [],
            'interventions': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Wound evidence from Vision (Person 1)
        if hasattr(casualty, 'wounds') and casualty.wounds:
            for wound in casualty.wounds:
                evidence['wounds'].append({
                    'type': getattr(wound, 'type', 'unknown'),
                    'severity': getattr(wound, 'severity', 0.5),
                    'bleeding': getattr(wound, 'bleeding', False),
                    'location': getattr(wound, 'body_region', 'unknown'),
                    'size_cm2': getattr(wound, 'size_cm2', 0),
                    'confidence': getattr(wound, 'confidence', 0.8)
                })
        
        # Audio evidence from Person 2's suggestions
        if 'app_state' in globals():
            audio_suggestions = [s for s in app_state.get_pending_suggestions() 
                               if s.casualty_id == casualty.id and s.source == "audio"]
            for suggestion in audio_suggestions:
                evidence['audio_findings'].append({
                    'classification': suggestion.suggested_category,
                    'confidence': suggestion.confidence,
                    'details': suggestion.reasoning
                })
        else:
            # Test data for Neal's audio format
            evidence['audio_findings'] = [
                {
                    'classification': 'NORMAL',
                    'confidence': 0.9
                }
            ]
        
        # Previous interventions
        evidence['interventions'] = self.get_casualty_interventions(
            getattr(casualty, 'id', 'TEST')
        )
        
        return evidence
    
    def calculate_triage_scores(self, evidence: Dict) -> Dict:
        """
        Enhanced SALT/TCCC scoring algorithm
        Returns numerical scores for different risk factors
        """
        scores = {
            'wound_score': 0,
            'bleeding_score': 0,
            'respiratory_score': 0,
            'location_score': 0,
            'consciousness_score': 5,  # Assume conscious unless indicated
            'total_score': 0
        }
        
        # Wound scoring
        for wound in evidence['wounds']:
            # Base severity (0-1 scale to 0-10 scale)
            scores['wound_score'] += wound['severity'] * 10
            
            # Bleeding penalty (major risk factor)
            if wound['bleeding']:
                scores['bleeding_score'] += 15
            
            # Location criticality (anatomical priority)
            location = wound['location'].lower()
            if location in ['head', 'neck']:
                scores['location_score'] += 20  # Critical airway/neurological
            elif location in ['torso', 'chest', 'abdomen']:
                scores['location_score'] += 15  # Vital organs
            elif location in ['limb', 'arm', 'leg']:
                scores['location_score'] += 5   # Less critical
                
            # Size factor
            size_penalty = min(wound.get('size_cm2', 0) / 10, 5)  # Cap at 5 points
            scores['wound_score'] += size_penalty
        
        # Enhanced audio/respiratory scoring (Neal's format)
        for finding in evidence['audio_findings']:
            classification = str(finding.get('classification', '')).upper()
            confidence = finding.get('confidence', 0.5)
            
            if 'AIRWAY COMPROMISE' in classification:
                scores['respiratory_score'] += 25 * confidence  # Immediate life threat
            elif 'POSSIBLE AIRWAY COMPROMISE' in classification:
                scores['respiratory_score'] += 15 * confidence  # Significant concern
            elif 'DISTRESS' in classification:
                scores['respiratory_score'] += 20 * confidence  # Respiratory distress
            elif 'ABNORMAL' in classification:
                scores['respiratory_score'] += 10 * confidence  # Abnormal but stable
            # NORMAL adds no score
        
        # Calculate total with medical weights
        scores['total_score'] = (
            scores['wound_score'] * 1.0 +        # Base wound severity
            scores['bleeding_score'] * 1.5 +     # Bleeding weighted higher
            scores['respiratory_score'] * 1.4 +   # Respiratory critical
            scores['location_score'] * 1.3 +     # Anatomical priority
            max(0, 10 - scores['consciousness_score']) * 2.0  # Consciousness
        )
        
        return scores
    
    def determine_priority(self, scores: Dict) -> TriageCategory:
        """
        Map numerical scores to SALT triage priorities
        Conservative bias - round up when uncertain
        NEVER suggests BLACK/EXPECTANT (medic-only decision)
        """
        total = scores['total_score']
        bleeding = scores['bleeding_score']
        respiratory = scores['respiratory_score']
        location = scores['location_score']
        
        # RED (Immediate) criteria - immediate life threats
        if (total >= 50 or 
            bleeding >= 20 or 
            respiratory >= 25 or
            location >= 20):
            return TriageCategory.RED
        
        # YELLOW (Delayed) criteria - urgent but not immediate
        if (total >= 25 or
            bleeding >= 10 or
            respiratory >= 15 or
            scores['wound_score'] >= 20):
            return TriageCategory.YELLOW
        
        # GREEN (Minimal) - walking wounded
        return TriageCategory.GREEN
    
    def generate_medevac_9_line(self, casualty_id: str) -> Dict:
        """
        Generate standard 9-line MEDEVAC request
        Triggered by voice command or UI button
        """
        if 'app_state' in globals():
            casualty = app_state.get_casualty(casualty_id)
        else:
            casualty = None
            
        if not casualty and 'app_state' in globals():
            return {}
        
        # Build 9-line format
        nine_line = {
            'line_1_location': f'GRID {self.get_gps_coordinates(casualty_id)}',
            'line_2_radio_freq': '142.375 MHz',  # Standard MEDEVAC freq
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
        
        # Trigger MEDEVAC panel in UI
        if 'app_state' in globals():
            app_state.set_active_medevac(casualty_id, nine_line)
        
        # Log the MEDEVAC request
        self.log_medevac_request(casualty_id, nine_line)
        
        return nine_line
    
    def get_gps_coordinates(self, casualty_id: str) -> str:
        """Get GPS coordinates from mobile data if available"""
        # TODO: Get from Person 3's mobile data
        return "TBD - AWAITING GPS"
    
    def get_medevac_justification(self, casualty_id: str) -> str:
        """Get medical justification for MEDEVAC request"""
        try:
            # Get latest triage analysis
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT suggested_priority, reasoning 
                    FROM triage_decisions 
                    WHERE casualty_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (casualty_id,))
                
                result = cursor.fetchone()
                if result:
                    priority, reasoning_json = result
                    reasoning = json.loads(reasoning_json)
                    return f"{priority} PRIORITY: {'; '.join(reasoning[:2])}"
                    
        except Exception as e:
            print(f"Error getting justification: {e}")
            
        return "MEDICAL EVACUATION REQUIRED"
    
    def determine_special_equipment(self, casualty) -> str:
        """Determine special equipment needed for MEDEVAC"""
        equipment = []
        
        if casualty and hasattr(casualty, 'wounds') and casualty.wounds:
            for wound in casualty.wounds:
                if getattr(wound, 'bleeding', False):
                    equipment.append('BLOOD PRODUCTS')
                if getattr(wound, 'body_region', '') in ['head', 'neck']:
                    equipment.append('AIRWAY MANAGEMENT')
                if getattr(wound, 'severity', 0) > 0.7:
                    equipment.append('SURGICAL CAPABILITY')
        
        return ', '.join(equipment) if equipment else 'NONE'
    
    def get_patient_priority_counts(self) -> str:
        """Get count of patients by priority for 9-line"""
        if 'app_state' not in globals():
            return "RED: 1, YELLOW: 0, GREEN: 0"
            
        casualties = app_state.get_roster()
        counts = {'RED': 0, 'YELLOW': 0, 'GREEN': 0, 'BLACK': 0}
        
        for casualty in casualties:
            if hasattr(casualty, 'triage_category') and casualty.triage_category:
                category = casualty.triage_category.value if hasattr(casualty.triage_category, 'value') else str(casualty.triage_category)
                counts[category] = counts.get(category, 0) + 1
        
        return f"RED: {counts['RED']}, YELLOW: {counts['YELLOW']}, GREEN: {counts['GREEN']}"
    
    def log_triage_decision(self, suggestion):
        """Persist triage decision to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO triage_decisions 
                    (casualty_id, suggested_priority, confidence, reasoning, evidence, timestamp, llm_enhanced)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    getattr(suggestion, 'casualty_id', suggestion.get('casualty_id')),
                    str(getattr(suggestion, 'suggested_category', suggestion.get('suggested_category'))),
                    getattr(suggestion, 'confidence', suggestion.get('confidence')),
                    json.dumps(getattr(suggestion, 'reasoning', suggestion.get('reasoning'))),
                    json.dumps(getattr(suggestion, 'supporting_evidence', suggestion.get('supporting_evidence'))),
                    getattr(suggestion, 'timestamp', suggestion.get('timestamp', datetime.now())).isoformat() if hasattr(getattr(suggestion, 'timestamp', suggestion.get('timestamp')), 'isoformat') else str(getattr(suggestion, 'timestamp', suggestion.get('timestamp'))),
                    suggestion.get('llm_enhanced', True)
                ))
        except Exception as e:
            print(f"Failed to log triage decision: {e}")
    
    def log_medevac_request(self, casualty_id: str, nine_line: Dict):
        """Log MEDEVAC request to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO casualty_history 
                (casualty_id, timestamp, data, source)
                VALUES (?, ?, ?, ?)
            """, (
                casualty_id,
                datetime.now().isoformat(),
                json.dumps(nine_line),
                'medevac_request'
            ))
    
    def get_casualty_interventions(self, casualty_id: str) -> List[Dict]:
        """Get intervention history for casualty"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT intervention_type, location, timestamp, notes
                    FROM interventions 
                    WHERE casualty_id = ?
                    ORDER BY timestamp DESC
                """, (casualty_id,))
                
                return [
                    {
                        'type': row[0],
                        'location': row[1], 
                        'timestamp': row[2],
                        'notes': row[3]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            print(f"Error getting interventions: {e}")
            return []
    
    def log_intervention(self, casualty_id: str, intervention_type: str, 
                        location: str = None, notes: str = None):
        """Log medical intervention"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO interventions 
                (casualty_id, intervention_type, location, timestamp, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                casualty_id,
                intervention_type,
                location,
                datetime.now().isoformat(),
                notes
            ))
        
        # Also add to AppState if available
        if 'app_state' in globals():
            intervention = Intervention(
                casualty_id=casualty_id,
                type=intervention_type,
                location=location,
                timestamp=datetime.now(),
                notes=notes
            )
            app_state.add_intervention(casualty_id, intervention)


# Main interface for integration
def start_triage_engine():
    """Initialize and start the triage engine"""
    engine = TriageEngine()
    
    print(f"🏥 Triage Engine initialized")
    print(f"🧠 LLM integration: {'✅ Available' if engine.llm_analyzer.available else '❌ Unavailable'}")
    print(f"💾 Database: {engine.db_path}")
    
    # Process all casualties periodically (only if AppState available)
    if 'app_state' in globals():
        import threading
        import time
        
        def processing_loop():
            while True:
                try:
                    engine.process_all_casualties()
                    time.sleep(5)  # Process every 5 seconds
                except Exception as e:
                    app_state.audit("triage_engine", "loop_error", str(e))
                    time.sleep(10)  # Longer wait on error
        
        # Start background processing
        thread = threading.Thread(target=processing_loop, daemon=True)
        thread.start()
        print("🔄 Background processing started")
    else:
        print("⏳ Background processing will start once AppState is available")
    
    return engine

# Export for team integration
__all__ = ['TriageEngine', 'start_triage_engine']

# Test functionality if run directly
if __name__ == "__main__":
    print("🏥 TRIAGE ENGINE - STANDALONE TEST")
    print("=" * 50)
    
    # Test engine creation
    engine = TriageEngine()
    
    # Test with mock casualty
    class MockCasualty:
        def __init__(self):
            self.id = "TEST_001"
            self.wounds = [MockWound()]
    
    class MockWound:
        def __init__(self):
            self.type = "laceration"
            self.severity = 0.8
            self.bleeding = True
            self.body_region = "torso"
            self.size_cm2 = 12.5
            self.confidence = 0.9
    
    mock_casualty = MockCasualty()
    
    print("\n🧪 Testing analysis with LLM enhancement...")
    result = engine.analyze_casualty(mock_casualty)
    
    if result:
        print("✅ Analysis successful!")
        print(f"Priority: {result['suggested_category']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"LLM Enhanced: {result.get('llm_enhanced', False)}")
    
    print("\n🚁 Testing MEDEVAC generation...")
    nine_line = engine.generate_medevac_9_line("TEST_001")
    print("✅ MEDEVAC 9-line generated:")
    for key, value in nine_line.items():
        print(f"  {key}: {value}")
    
    print("\n🎯 Triage engine ready for integration!")