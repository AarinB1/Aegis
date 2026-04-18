import { Container } from "../ui/Container";
import { Overline } from "../ui/Overline";
import { Reveal, RevealStagger, RevealItem } from "../ui/Reveal";

const guardrails = [
  {
    heading: "Every suggestion requires medic confirmation.",
    description:
      "Triage categories, interventions, and MEDEVAC sends all round-trip through an explicit human confirmation step. AEGIS proposes — the medic decides.",
  },
  {
    heading: "Expectant (black) cannot be AI-assigned.",
    description:
      "The system is prohibited in code from suggesting an expectant categorization. That determination is medic-only. Always.",
  },
  {
    heading: "Every AI-derived field carries a confidence score.",
    description:
      "Wound masks, respiratory classifications, and triage proposals display calibrated confidence. Low-confidence signals surface as prompts, not claims.",
  },
  {
    heading: "Full local audit log.",
    description:
      "Every suggestion, confirmation, override, and voice command is written to a local SQLite log with timestamps and provenance — for after-action review.",
  },
  {
    heading: "One-toggle manual override.",
    description:
      "AI suggestions can be disabled entirely with a single switch. The dashboard keeps working as a structured casualty tracker without any autonomy.",
  },
  {
    heading: "Fully offline operation.",
    description:
      "AEGIS runs on a 20–40 W edge device with no network dependency. No cloud, no uplink, no data leaves the device — by default, not by configuration.",
  },
];

export function Ethics() {
  return (
    <section id="ethics" className="relative py-28 sm:py-36">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-surface/60"
      />
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-px bg-hairline"
      />
      <div
        aria-hidden
        className="absolute inset-x-0 bottom-0 h-px bg-hairline"
      />

      <Container className="relative">
        <Reveal className="mx-auto max-w-3xl">
          <Overline>Ethics & safety</Overline>
          <h2 className="mt-5 font-display text-[38px] font-normal leading-[1.04] tracking-display-tight sm:text-[56px]">
            Perception augmentation,
            <br />
            <span className="italic text-ink-muted">
              not autonomous triage.
            </span>
          </h2>
          <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-ink-muted sm:text-base">
            AEGIS never makes a life-or-death decision. It surfaces
            information faster so the medic can. These are the guardrails
            enforced in code, not policy.
          </p>
        </Reveal>

        <RevealStagger
          stagger={0.06}
          delayChildren={0.05}
          className="mt-16 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-hairline bg-hairline md:grid-cols-2 lg:grid-cols-3"
        >
          {guardrails.map((g) => (
            <RevealItem
              key={g.heading}
              className="flex flex-col gap-3 bg-paper p-7"
            >
              <div className="flex items-center gap-2">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  aria-hidden
                  className="text-accent"
                >
                  <path
                    d="M7 1l5 2v4c0 3-2.3 5.5-5 6-2.7-.5-5-3-5-6V3l5-2Z"
                    fill="currentColor"
                    fillOpacity="0.12"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M4.6 7.2l1.7 1.7L9.6 5.6"
                    stroke="currentColor"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                </svg>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-muted">
                  Guardrail
                </span>
              </div>
              <h3 className="font-display text-[19px] font-normal leading-snug tracking-tight text-ink">
                {g.heading}
              </h3>
              <p className="text-sm leading-relaxed text-ink-muted">
                {g.description}
              </p>
            </RevealItem>
          ))}
        </RevealStagger>
      </Container>
    </section>
  );
}
