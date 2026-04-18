"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Container } from "../ui/Container";
import { LinkButton } from "../ui/Button";
import { Overline } from "../ui/Overline";
import { DashboardMock } from "../mocks/DashboardMock";

export function Hero() {
  const prefersReduced = useReducedMotion();

  const fadeUp = (delay: number) => ({
    initial: { opacity: 0, y: prefersReduced ? 0 : 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1], delay },
  });

  return (
    <section id="top" className="relative pt-32 sm:pt-40">
      {/* Soft background grid behind mockup */}
      <div
        aria-hidden
        className="bg-grid-paper pointer-events-none absolute inset-x-0 top-0 h-[780px] opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]"
      />

      <Container className="relative">
        <div className="mx-auto max-w-4xl text-center">
          <motion.div {...fadeUp(0)}>
            <Overline className="justify-center">
              AI-Enhanced Guidance for Integrated Survival
            </Overline>
          </motion.div>

          <motion.h1
            {...fadeUp(0.08)}
            className="mt-6 font-display text-[44px] font-normal leading-[1.02] tracking-display-tight text-ink sm:text-6xl lg:text-7xl"
          >
            A shield of perception
            <br />
            <span className="italic text-ink-muted">
              for those who shield others.
            </span>
          </motion.h1>

          <motion.p
            {...fadeUp(0.16)}
            className="mx-auto mt-7 max-w-2xl text-[17px] leading-relaxed text-ink-muted sm:text-lg"
          >
            AEGIS is an edge-deployable AI copilot that extends one combat
            medic&rsquo;s perception across dozens of casualties during Mass
            Casualty events — fusing vision, audio, and voice to support SALT
            and TCCC triage in fully disconnected environments.
          </motion.p>

          <motion.div
            {...fadeUp(0.24)}
            className="mt-9 flex flex-wrap items-center justify-center gap-3"
          >
            <LinkButton href="http://localhost:8501" variant="primary">
              Launch Dashboard
              <svg
                width="12"
                height="12"
                viewBox="0 0 12 12"
                aria-hidden
                className="opacity-80"
              >
                <path
                  d="M3 9l6-6M5 3h4v4"
                  stroke="currentColor"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
            </LinkButton>
            <LinkButton
              href="https://github.com/aarinb1/aegis"
              variant="secondary"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
                aria-hidden
              >
                <path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.08-2.7-1.08-.36-.92-.89-1.17-.89-1.17-.73-.5.05-.49.05-.49.8.06 1.23.83 1.23.83.72 1.22 1.87.87 2.33.66.07-.52.28-.87.5-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 4 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
              </svg>
              View on GitHub
            </LinkButton>
          </motion.div>

          <motion.div
            {...fadeUp(0.32)}
            className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-1 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted"
          >
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-triage-green" />
              Fully offline
            </span>
            <span className="opacity-60">·</span>
            <span>Jetson Orin · 20–40 W</span>
            <span className="opacity-60">·</span>
            <span>SALT · TCCC aligned</span>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: prefersReduced ? 0 : 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 1,
            ease: [0.22, 1, 0.36, 1],
            delay: 0.4,
          }}
          className="relative mx-auto mt-20 max-w-6xl"
        >
          {/* Accent shadow under the mock */}
          <div
            aria-hidden
            className="absolute inset-x-10 -bottom-8 h-24 rounded-full bg-ink/10 blur-3xl"
          />
          <DashboardMock />
        </motion.div>
      </Container>
    </section>
  );
}
