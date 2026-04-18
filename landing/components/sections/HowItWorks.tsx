import { Container } from "../ui/Container";
import { Overline } from "../ui/Overline";
import { Reveal, RevealStagger, RevealItem } from "../ui/Reveal";

const steps = [
  {
    n: "01",
    heading: "Detect & track",
    description:
      "Every casualty in frame gets a persistent track ID the moment they appear. Smoke, partial occlusion, and re-entry don't break the roster.",
  },
  {
    n: "02",
    heading: "Assess & segment",
    description:
      "Wounds are localized and measured. Respiratory sounds are classified. Posture, motion, and pulse-present cues are fused per casualty.",
  },
  {
    n: "03",
    heading: "Confirm & triage",
    description:
      "The fusion engine proposes a SALT category with confidence. The medic confirms by voice or tap. Nothing is committed autonomously.",
  },
  {
    n: "04",
    heading: "Evacuate",
    description:
      "Once triaged, a 9-Line MEDEVAC drafts itself from the roster. The medic reviews, edits, and sends — mesh, radio, or runner.",
  },
];

export function HowItWorks() {
  return (
    <section className="py-28 sm:py-36">
      <Container>
        <Reveal className="mx-auto max-w-2xl text-center">
          <Overline className="justify-center">How it works</Overline>
          <h2 className="mt-5 font-display text-[36px] font-normal leading-[1.08] tracking-display-tight sm:text-5xl">
            Four stages, one loop,
            <br />
            <span className="italic text-ink-muted">always medic-confirmed.</span>
          </h2>
        </Reveal>

        <RevealStagger
          stagger={0.08}
          delayChildren={0.05}
          className="mt-16 grid grid-cols-1 gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-4"
        >
          {steps.map((s, i) => (
            <RevealItem key={s.n}>
              <div className="relative">
                <div className="flex items-baseline gap-3">
                  <span
                    aria-hidden
                    className="tabular font-display text-[54px] font-light leading-none tracking-display-tight text-accent"
                  >
                    {s.n}
                  </span>
                  {i < steps.length - 1 ? (
                    <span
                      aria-hidden
                      className="hidden flex-1 translate-y-[-10px] border-t border-dashed border-hairline lg:block"
                    />
                  ) : null}
                </div>
                <h3 className="mt-5 font-display text-xl font-normal tracking-tight text-ink">
                  {s.heading}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                  {s.description}
                </p>
              </div>
            </RevealItem>
          ))}
        </RevealStagger>
      </Container>
    </section>
  );
}
