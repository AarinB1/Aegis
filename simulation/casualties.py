import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from triage_engine import get_priority_and_reasoning
from schema import Casualty, Wound, TriageCategory, RespiratoryStatus


class SimCasualty:
    def __init__(self, cid, location, audio_file, image_file, priority, output_script):
        self.id = cid
        self.location = location
        self.audio = audio_file
        self.image = image_file
        self.priority = priority
        self.output_script = output_script
        self.reasoning = ""


def get_casualties():
    casualties = [
        SimCasualty(
            cid="A1",
            location=(38.99, -76.94),
            audio_file="../audio/normal.wav",
            image_file="../audio/normal.wav",
            priority=2,
            output_script="this person has their face off"
        ),
        SimCasualty(
            cid="A2",
            location=(38.9905, -76.941),
            audio_file="../audio/testclip.wav",
            image_file="../audio/normal.wav",
            priority=1,
            output_script="this person has something going on"
        ),
    ]
    return casualties


def sim_to_real(sim):
    return Casualty(
        casualty_id=sim.id,
        triage_category=TriageCategory.UNASSESSED,
        responsive=True,
        respiratory_status=RespiratoryStatus.UNKNOWN,
        respiratory_rate=20,
        wounds=[
            Wound(
                location="unknown",
                area_cm2=5.0,
                severity="moderate",
                active_bleeding=True,
                ai_confidence=0.8
            )
        ]
    )


def evaluate_all():
    casualties = get_casualties()
    results = []

    for sim in casualties:
        real = sim_to_real(sim)
        priority, reasoning = get_priority_and_reasoning(real)
        sim.priority = priority
        sim.reasoning = reasoning
        results.append(sim)

    return results

if __name__ == "__main__":

    results = evaluate_all()

    for c in results:

        print(f"ID: {c.id}")

        print(f"Priority: {c.priority}")

        print(f"Reasoning: {c.reasoning}")

        print("-" * 30)