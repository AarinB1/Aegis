import { Container } from "../ui/Container";
import { Reveal } from "../ui/Reveal";

const items = [
  "SALT Triage",
  "TCCC",
  "9-Line MEDEVAC",
  "DIL environments",
  "SOCOM-grade doctrine",
];

export function Supports() {
  return (
    <section className="py-28 sm:py-36">
      <Container>
        <Reveal>
          <div className="flex flex-col items-center gap-6 text-center">
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink-muted">
              Aligned with doctrine
            </span>
            <ul className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-[15px] text-ink/70">
              {items.map((item, i) => (
                <li key={item} className="flex items-center gap-10">
                  <span className="font-display text-xl font-light tracking-tight">
                    {item}
                  </span>
                  {i < items.length - 1 ? (
                    <span
                      aria-hidden
                      className="hidden h-1 w-1 rounded-full bg-ink/25 md:inline-block"
                    />
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
