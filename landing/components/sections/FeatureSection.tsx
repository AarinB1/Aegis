import { ReactNode } from "react";
import { Container } from "../ui/Container";
import { Overline } from "../ui/Overline";
import { Reveal } from "../ui/Reveal";

type SubPoint = {
  heading: string;
  description: string;
};

type Props = {
  id?: string;
  overline: string;
  heading: ReactNode;
  paragraph: string;
  points: SubPoint[];
  mock: ReactNode;
  reverse?: boolean;
};

export function FeatureSection({
  id,
  overline,
  heading,
  paragraph,
  points,
  mock,
  reverse = false,
}: Props) {
  return (
    <section id={id} className="py-24 sm:py-32">
      <Container>
        <div
          className={`grid grid-cols-1 items-center gap-12 lg:grid-cols-12 lg:gap-16 ${
            reverse ? "lg:[&>*:first-child]:order-2" : ""
          }`}
        >
          <Reveal className="lg:col-span-5">
            <Overline>{overline}</Overline>
            <h2 className="mt-5 font-display text-[34px] font-normal leading-[1.08] tracking-display-tight sm:text-5xl">
              {heading}
            </h2>
            <p className="mt-6 max-w-md text-[15px] leading-relaxed text-ink-muted sm:text-base">
              {paragraph}
            </p>

            <dl className="mt-10 space-y-7">
              {points.map((p) => (
                <div key={p.heading}>
                  <dt className="font-display text-lg font-normal tracking-tight text-ink">
                    {p.heading}
                  </dt>
                  <dd className="mt-1.5 text-sm leading-relaxed text-ink-muted">
                    {p.description}
                  </dd>
                </div>
              ))}
            </dl>
          </Reveal>

          <Reveal delay={0.08} className="lg:col-span-7">
            <div className="relative">
              <div
                aria-hidden
                className="absolute -inset-6 -z-10 rounded-3xl bg-surface/50"
              />
              {mock}
            </div>
          </Reveal>
        </div>
      </Container>
    </section>
  );
}
