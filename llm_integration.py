# llm_integration.py - Ollama integration for Python triage engine

import requests
import json
from typing import Dict, List, Optional

class OllamaTriageAnalyzer:
    """
    Integrates Ollama/Llama for enhanced medical reasoning
    Works with your existing rule-based system
    """
    
    def __init__(self, base_url="http://127.0.0.1:11434", model="llama3.2:latest"):
        self.base_url = base_url
        self.model = model
        self.available = self.check_ollama_connection()
    
    def check_ollama_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def enhance_triage_reasoning(self, evidence: Dict, rule_based_scores: Dict, 
                               rule_based_priority: str) -> Dict:
        """
        Enhance rule-based triage with LLM reasoning
        Falls back to rule-based if LLM fails
        """
        if not self.available:
            return {
                'priority': rule_based_priority,
                'reasoning': ['Using rule-based analysis (LLM unavailable)'],
                'confidence': 0.8,
                'source': 'rule_based_fallback'
            }
        
        try:
            # Prepare medical context for LLM
            prompt = self.build_medical_prompt(evidence, rule_based_scores, rule_based_priority)
            
            # Call Ollama
            response = self.call_ollama(prompt)
            
            # Parse LLM response
            llm_result = self.parse_llm_response(response)
            
            # Validate LLM output against rules (safety check)
            validated_result = self.validate_llm_output(llm_result, rule_based_priority)
            
            return validated_result
            
        except Exception as e:
            print(f"LLM enhancement failed: {e}")
            return {
                'priority': rule_based_priority,
                'reasoning': ['Using rule-based analysis (LLM error)'],
                'confidence': 0.8,
                'source': 'rule_based_fallback'
            }
    
    def build_medical_prompt(self, evidence: Dict, scores: Dict, rule_priority: str) -> str:
        """Build specialized medical prompt for combat triage"""
        
        # Handle Neal's audio classifications
        audio_status = self.interpret_audio_findings(evidence.get('audio_findings', []))
        
        prompt = f"""
You are an expert combat medic AI trained in SALT and TCCC protocols. Analyze this casualty data and provide triage reasoning.

CASUALTY EVIDENCE:
Wounds: {json.dumps(evidence.get('wounds', []), indent=2)}
Audio Analysis: {audio_status}
Previous Interventions: {evidence.get('interventions', [])}

RULE-BASED ANALYSIS:
Scores: {json.dumps(scores, indent=2)}
Suggested Priority: {rule_priority}

MEDICAL CONTEXT:
- This is a combat/mass casualty scenario
- Conservative bias required (round up when uncertain)  
- NEVER suggest BLACK/EXPECTANT (medic-only decision)
- Focus on immediate life threats

TASK:
Provide triage assessment in this exact JSON format:
{{
  "priority": "RED|YELLOW|GREEN",
  "confidence": 0.85,
  "reasoning": [
    "Specific medical finding 1",
    "Specific medical finding 2", 
    "Clinical justification"
  ],
  "recommended_actions": [
    "Immediate action 1",
    "Monitoring requirement",
    "Treatment priority"
  ]
}}

Respond ONLY with valid JSON. No additional text.
"""
        return prompt
    
    def interpret_audio_findings(self, audio_findings: List[Dict]) -> str:
        """Interpret Neal's audio output format"""
        if not audio_findings:
            return "No audio analysis available"
        
        interpretations = []
        for finding in audio_findings:
            classification = finding.get('classification', 'UNKNOWN')
            confidence = finding.get('confidence', 0.0)
            
            if classification == 'AIRWAY COMPROMISE':
                interpretations.append(f"CRITICAL: Airway compromise detected (conf: {confidence:.2f})")
            elif classification == 'POSSIBLE AIRWAY COMPROMISE':
                interpretations.append(f"WARNING: Possible airway compromise (conf: {confidence:.2f})")
            elif classification == 'NORMAL':
                interpretations.append(f"Normal breathing pattern (conf: {confidence:.2f})")
            else:
                interpretations.append(f"Unknown audio pattern: {classification} (conf: {confidence:.2f})")
        
        return "; ".join(interpretations)
    
    def call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent medical decisions
                    "top_p": 0.9,
                    "num_predict": 500
                }
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
    
    def parse_llm_response(self, response: str) -> Dict:
        """Parse LLM JSON response"""
        try:
            # Try to find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            raise ValueError(f"Failed to parse LLM response: {e}")
    
    def validate_llm_output(self, llm_result: Dict, rule_priority: str) -> Dict:
        """
        Validate LLM output for medical safety
        Ensure conservative bias is maintained
        """
        validated = llm_result.copy()
        
        # Ensure valid priority
        valid_priorities = ['RED', 'YELLOW', 'GREEN']
        if validated.get('priority') not in valid_priorities:
            validated['priority'] = rule_priority
        
        # Never allow BLACK from LLM
        if validated.get('priority') == 'BLACK':
            validated['priority'] = 'RED'  # Conservative bias
            validated['reasoning'].append("Elevated to RED (no automatic BLACK assignment)")
        
        # Ensure confidence is reasonable
        confidence = validated.get('confidence', 0.8)
        if not 0.0 <= confidence <= 1.0:
            validated['confidence'] = 0.8
        
        # Conservative bias check - don't downgrade from rule-based priority
        priority_levels = {'GREEN': 1, 'YELLOW': 2, 'RED': 3}
        rule_level = priority_levels.get(rule_priority, 2)
        llm_level = priority_levels.get(validated['priority'], 2)
        
        if llm_level < rule_level:
            validated['priority'] = rule_priority
            validated['reasoning'].append(f"Maintained rule-based priority {rule_priority} (conservative bias)")
        
        validated['source'] = 'llm_enhanced'
        return validated


# Integration with your triage engine
def integrate_ollama_with_triage_engine():
    """
    Update your existing triage engine to use Ollama
    Add this to your triage_engine.py
    """
    integration_code = '''
# Add to your triage_engine.py imports:
from llm_integration import OllamaTriageAnalyzer

class TriageEngine:
    def __init__(self, db_path="mascal.db"):
        self.db_path = db_path
        self.init_database()
        self.llm_analyzer = OllamaTriageAnalyzer()  # Add this line
    
    def analyze_casualty(self, casualty: Casualty) -> Optional[Suggestion]:
        """Enhanced analysis with Ollama integration"""
        try:
            evidence = self.gather_evidence(casualty)
            scores = self.calculate_triage_scores(evidence)
            rule_priority = self.determine_priority(scores)
            
            # NEW: Enhance with Ollama
            llm_result = self.llm_analyzer.enhance_triage_reasoning(
                evidence, scores, rule_priority.value
            )
            
            suggestion = Suggestion(
                casualty_id=casualty.id,
                suggested_category=TriageCategory[llm_result['priority']],
                confidence=llm_result['confidence'],
                reasoning=llm_result['reasoning'],
                source="triage_engine_llm",
                supporting_evidence=evidence,
                timestamp=datetime.now()
            )
            
            return suggestion
            
        except Exception as e:
            app_state.audit("triage_engine", "analysis_error", f"Failed: {str(e)}")
            return None
    '''
    
    print("Integration code for triage_engine.py:")
    print(integration_code)

if __name__ == "__main__":
    # Test Ollama integration
    analyzer = OllamaTriageAnalyzer()
    
    if analyzer.available:
        print("✅ Ollama connection successful!")
        print(f"Model: {analyzer.model}")
        
        # Test with Neal's audio format
        test_evidence = {
            'wounds': [
                {
                    'type': 'laceration',
                    'severity': 0.8,
                    'bleeding': True,
                    'location': 'torso',
                    'size_cm2': 12.0,
                    'confidence': 0.9
                }
            ],
            'audio_findings': [
                {
                    'classification': 'AIRWAY COMPROMISE',
                    'confidence': 0.85
                }
            ],
            'interventions': []
        }
        
        test_scores = {'total_score': 55, 'wound_score': 25, 'bleeding_score': 20}
        
        result = analyzer.enhance_triage_reasoning(test_evidence, test_scores, 'RED')
        print("\n🧠 LLM Enhanced Analysis:")
        print(json.dumps(result, indent=2))
        
    else:
        print("❌ Ollama not available")
        print("Make sure Ollama is running: ollama serve")
    
    integrate_ollama_with_triage_engine()