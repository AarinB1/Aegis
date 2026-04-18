# llm_integration.py - Ollama/Llama 3.2 integration for triage reasoning
import json
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


class OllamaTriageAnalyzer:
    """
    Wraps a local Ollama/Llama 3.2 model to enhance rule-based triage
    with natural-language medical reasoning.

    Falls back to rule-based output if Ollama isn't running. Never
    overrides the rule engine's priority - LLM only explains WHY.
    """

    def __init__(self, model=OLLAMA_MODEL, url=OLLAMA_URL, timeout=8):
        self.model = model
        self.url = url
        self.timeout = timeout
        self.available = self._check_ollama()

    def _check_ollama(self):
        """Quick probe to see if Ollama is running locally."""
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def enhance_triage_reasoning(self, evidence, scores, rule_priority):
        """
        Ask Llama to explain the rule-based decision in clinical language.
        Returns dict with: priority, confidence, reasoning (list), source.
        """
        if not self.available:
            return self._fallback(rule_priority, evidence, scores)

        prompt = self._build_prompt(evidence, scores, rule_priority)

        try:
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_predict": 300}
            }).encode("utf-8")

            req = urllib.request.Request(
                self.url, data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            llm_text = raw.get("response", "").strip()
            parsed = json.loads(llm_text)

            # LLM's priority is advisory only - we KEEP the rule-based priority
            # for safety. LLM just provides the reasoning.
            reasoning = parsed.get("reasoning", [])
            if isinstance(reasoning, str):
                reasoning = [reasoning]
            if not reasoning:
                reasoning = ["Llama unable to produce reasoning; using rule-based logic"]

            confidence = float(parsed.get("confidence", 0.8))
            confidence = max(0.0, min(1.0, confidence))

            return {
                "priority": rule_priority,  # Rule engine wins for safety
                "confidence": confidence,
                "reasoning": reasoning[:3],
                "source": "llama_3.2_enhanced"
            }

        except (urllib.error.URLError, json.JSONDecodeError, KeyError, ValueError) as e:
            return self._fallback(rule_priority, evidence, scores,
                                  error=f"LLM error: {type(e).__name__}")

    def _build_prompt(self, evidence, scores, rule_priority):
        wounds_summary = []
        for w in evidence.get("wounds", []):
            wounds_summary.append(
                f"- {w.get('location', 'unknown')}: "
                f"severity={w.get('severity', 0):.1f}, "
                f"bleeding={w.get('bleeding', False)}, "
                f"area_cm2={w.get('area_cm2', 0)}"
            )
        wounds_text = "\n".join(wounds_summary) if wounds_summary else "- none documented"

        vitals = evidence.get("vitals", {})
        audio = evidence.get("audio_findings", [])
        audio_text = ", ".join(f.get("classification", "UNKNOWN") for f in audio) if audio else "none"

        return f"""You are a combat medic assistant applying SALT/TCCC triage doctrine.
A rule-based engine has already classified this casualty as: {rule_priority.upper()}.

Your job: provide 2-3 short clinical reasoning bullets explaining WHY this priority
is appropriate. You do NOT change the priority - you justify it.

CASUALTY EVIDENCE:
Wounds:
{wounds_text}

Vitals:
- Respiratory status: {vitals.get('respiratory_status', 'unknown')}
- Respiratory rate: {vitals.get('respiratory_rate', 'unknown')}
- Responsive: {vitals.get('responsive', 'unknown')}

Audio findings: {audio_text}

Scores: bleeding={scores.get('bleeding_score', 0)}, respiratory={scores.get('respiratory_score', 0)}, location={scores.get('location_score', 0)}, total={scores.get('total_score', 0):.1f}

Respond ONLY with valid JSON in this exact format:
{{"reasoning": ["bullet 1", "bullet 2", "bullet 3"], "confidence": 0.85}}

Keep each bullet under 15 words. Use TCCC/SALT terminology. No preamble, just JSON."""

    def _fallback(self, rule_priority, evidence, scores, error=None):
        reasoning = []

        if scores.get("bleeding_score", 0) >= 15:
            reasoning.append("Active hemorrhage detected - MARCH protocol M priority")
        if scores.get("location_score", 0) >= 20:
            reasoning.append("Head/neck wound - airway risk elevates acuity")
        elif scores.get("location_score", 0) >= 15:
            reasoning.append("Torso wound - potential for internal injury")
        if scores.get("respiratory_score", 0) >= 20:
            reasoning.append("Respiratory compromise identified - airway priority")
        if not reasoning:
            wc = len(evidence.get("wounds", []))
            reasoning.append(f"{wc} wound(s) assessed, vitals within compensated range")

        note = "Rule-based analysis"
        if error:
            note += f" ({error})"
        reasoning.append(note)

        return {
            "priority": rule_priority,
            "confidence": 0.8,
            "reasoning": reasoning[:3],
            "source": "rule_based_fallback"
        }


__all__ = ["OllamaTriageAnalyzer"]
