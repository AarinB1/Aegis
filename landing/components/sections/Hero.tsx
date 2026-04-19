import { LinkButton } from "../ui/Button";
import { Container } from "../ui/Container";
import { Overline } from "../ui/Overline";
import { Reveal, RevealItem, RevealStagger } from "../ui/Reveal";

const pillars = [
  {
    label: "Vision",
    value: "Tracks casualties, scores visible wound burden, and surfaces active hemorrhage first.",
  },
  {
    label: "Audio",
    value: "Flags respiratory distress and airway compromise when the scene is too loud to trust the ear alone.",
  },
  {
    label: "Triage",
    value: "Builds medic-confirmed SALT/TCCC suggestions and drafts MEDEVAC from the live roster.",
  },
];

export function Hero() {
  return (
    <section id="top" className="overflow-hidden border-b border-hairline bg-paper py-20 sm:py-24 lg:py-28">
      <Container>
        <div className="grid items-end gap-14 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
          <Reveal as="header" className="max-w-3xl">
            <Overline>Hackathon Build</Overline>
            <h1 className="mt-6 font-display text-[clamp(3.25rem,7vw,6.4rem)] font-normal leading-[0.95] tracking-display-tight text-ink">
              A shield of perception
              <br />
              <span className="italic text-ink-muted">for the medic on the ground.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-[1.05rem] leading-8 text-ink-muted sm:text-[1.12rem]">
              AEGIS helps one combat medic see more, hear more, and prioritize faster during
              MASCAL events. The system keeps casualty identity stable, estimates injury burden,
              and highlights who needs urgent care first without taking the human out of triage.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <LinkButton href="#features">Explore the system</LinkButton>
              <LinkButton
                href="https://github.com/AarinB1/Aegis"
                variant="secondary"
              >
                Open GitHub
              </LinkButton>
            </div>
          </Reveal>

          <Reveal className="relative">
            <div className="absolute inset-x-10 inset-y-12 -z-10 rounded-full bg-accent/10 blur-3xl" />
            <div className="rounded-[32px] border border-hairline bg-surface px-6 py-7 shadow-[0_30px_80px_rgba(24,21,17,0.08)] sm:px-8 sm:py-8">
              <div className="flex items-center justify-between gap-4 border-b border-hairline pb-4">
                <div>
                  <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted">
                    Live scene readout
                  </div>
                  <div className="mt-2 font-display text-3xl tracking-tight text-ink">
                    Focus casualty: A1
                  </div>
                </div>
                <div className="rounded-full bg-accent px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-paper">
                  Immediate
                </div>
              </div>

              <div className="mt-5 space-y-4 text-sm leading-7 text-ink-muted">
                <p>
                  Visible torso hemorrhage and multiple wound sites push A1 to the top of the
                  attention stack while the remaining casualties stay tracked in the scene.
                </p>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-hairline bg-paper px-4 py-4">
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
                      Tracked
                    </div>
                    <div className="mt-2 font-display text-3xl text-ink">03</div>
                  </div>
                  <div className="rounded-2xl border border-hairline bg-paper px-4 py-4">
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
                      Bleeding
                    </div>
                    <div className="mt-2 font-display text-3xl text-ink">02</div>
                  </div>
                  <div className="rounded-2xl border border-hairline bg-paper px-4 py-4">
                    <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
                      Doctrine
                    </div>
                    <div className="mt-2 font-display text-3xl text-ink">SALT</div>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>

        <RevealStagger
          stagger={0.07}
          delayChildren={0.12}
          className="mt-16 grid gap-4 md:grid-cols-3"
        >
          {pillars.map((pillar) => (
            <RevealItem key={pillar.label}>
              <div className="rounded-2xl border border-hairline bg-surface px-5 py-5">
                <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted">
                  {pillar.label}
                </div>
                <p className="mt-3 text-sm leading-7 text-ink-muted">{pillar.value}</p>
              </div>
            </RevealItem>
          ))}
        </RevealStagger>
      </Container>
    </section>
  );
}
