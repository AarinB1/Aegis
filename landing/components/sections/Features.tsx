import { FeatureSection } from "./FeatureSection";
import { VisionMock } from "../mocks/VisionMock";
import { AudioMock } from "../mocks/AudioMock";
import { TriageMock } from "../mocks/TriageMock";

export function Features() {
  return (
    <div id="features">
      <FeatureSection
        id="perception"
        overline="Perception"
        heading={
          <>
            Every wound seen.
            <br />
            <span className="italic text-ink-muted">
              Every casualty tracked.
            </span>
          </>
        }
        paragraph="The vision pipeline runs zero-shot on tactical edge hardware. It detects
          every casualty in frame, holds identity across chaotic scenes, and measures wounds
          the moment they come into view — no custom training, no cloud."
        points={[
          {
            heading: "Detect & track",
            description:
              "YOLOv8 with ByteTrack maintains persistent track IDs across partial occlusion, smoke, and low light.",
          },
          {
            heading: "Segment in situ",
            description:
              "MobileSAM and Grounding DINO localize and measure wounds on the fly — arterial bleeds get surfaced first.",
          },
          {
            heading: "Re-identify after loss",
            description:
              "DINOv2 embeddings recover the same casualty when they leave the frame and return, so the roster never breaks.",
          },
        ]}
        mock={<VisionMock />}
      />

      <FeatureSection
        id="audio"
        overline="Acoustics"
        heading={
          <>
            Listening for what
            <br />
            <span className="italic text-ink-muted">the noise hides.</span>
          </>
        }
        paragraph="In a MASCAL scene the ear is overwhelmed long before the eye. AEGIS runs
          zero-shot audio classification continuously and gives the medic their hands back
          with voice-first command, recognized at the edge."
        points={[
          {
            heading: "Zero-shot acoustic triage",
            description:
              "CLAP flags stridor, gurgling, agonal breathing, and absent respirations with calibrated confidence scores.",
          },
          {
            heading: "Respiratory rate, continuous",
            description:
              "Cycle detection estimates breaths per minute from ambient audio — surfaced alongside the visual track.",
          },
          {
            heading: "Voice command, hands-free",
            description:
              "Whisper parses tag calls, interventions, and MEDEVAC requests. Every command round-trips through confirmation.",
          },
        ]}
        mock={<AudioMock />}
        reverse
      />

      <FeatureSection
        id="triage"
        overline="Triage & MEDEVAC"
        heading={
          <>
            Doctrine in the loop.
            <br />
            <span className="italic text-ink-muted">Medic on the trigger.</span>
          </>
        }
        paragraph="The fusion engine reconciles vision, audio, and voice into a single
          casualty record aligned with SALT and TCCC. Every AI-derived field carries a
          confidence score. Nothing is committed without the medic's hand."
        points={[
          {
            heading: "SALT-aligned suggestions",
            description:
              "The engine proposes IMMEDIATE / DELAYED / MINIMAL categories from the fused signals — the medic confirms, amends, or overrides.",
          },
          {
            heading: "Interventions, logged",
            description:
              "Tourniquets, airway management, and pulse checks are captured by voice or tap with time-stamped provenance.",
          },
          {
            heading: "9-Line MEDEVAC, pre-filled",
            description:
              "Lines 1–8 draft automatically from the roster and scene metadata. The medic reviews the nine lines, not assembles them.",
          },
        ]}
        mock={<TriageMock />}
      />
    </div>
  );
}
