"use client";

import { ReactNode, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Container } from "../ui/Container";
import { Overline } from "../ui/Overline";
import { Reveal } from "../ui/Reveal";

type QA = { q: string; a: ReactNode };

const items: QA[] = [
  {
    q: "Is AEGIS making triage decisions autonomously?",
    a: (
      <>
        No. AEGIS is perception augmentation, not autonomous triage. Every
        suggestion — SALT category, intervention log, MEDEVAC send — requires
        explicit medic confirmation. The expectant (black) categorization
        cannot be AI-assigned at all; it is medic-only, enforced in code.
      </>
    ),
  },
  {
    q: "Does it work without internet?",
    a: (
      <>
        Yes, by design. AEGIS runs end-to-end on an edge device with no
        network dependency. No cloud, no uplink, no data leaves the device. A
        live demo includes disconnecting from wifi and showing the pipeline
        continues uninterrupted.
      </>
    ),
  },
  {
    q: "What hardware does it run on?",
    a: (
      <>
        The target edge platform is the NVIDIA Jetson Orin NX at 20–40 W,
        running the vision and audio pipelines at 15–30 fps. A laptop GPU
        serves as the reference platform at 30+ fps; CPU-only fallback runs
        at 5–10 fps for training and dry-run work.
      </>
    ),
  },
  {
    q: "How accurate is the wound detection?",
    a: (
      <>
        AEGIS uses zero-shot models (MobileSAM, Grounding DINO) — no custom
        training was performed for this proof-of-concept. Expect strong
        performance on clear, unobstructed views and meaningful degradation
        on smoke, blood-obscured tissue, and unusual angles. Every wound
        field ships with a confidence score; low-confidence signals surface
        as prompts, not claims.
      </>
    ),
  },
  {
    q: "Has this been clinically validated?",
    a: (
      <>
        No. AEGIS is a hackathon proof-of-concept demonstrating the
        perception layer. Production deployment would require clinical
        validation, IRB review, hardware ruggedization, and partnership with
        military medical research institutions such as USAISR and DHA.
      </>
    ),
  },
  {
    q: "Is the code open source?",
    a: (
      <>
        The AEGIS integration layer is MIT-licensed. It builds on open-source
        components with varying licenses — notably YOLOv8 (Ultralytics) is
        AGPL-3.0, so production deployment would likely swap in a
        permissively-licensed detector such as RT-DETR or YOLOX.
      </>
    ),
  },
];

export function FAQ() {
  return (
    <section id="faq" className="py-28 sm:py-36">
      <Container>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:gap-16">
          <Reveal className="lg:col-span-4">
            <Overline>FAQ</Overline>
            <h2 className="mt-5 font-display text-[36px] font-normal leading-[1.06] tracking-display-tight sm:text-5xl">
              Honest answers about
              <br />
              <span className="italic text-ink-muted">
                a high-stakes tool.
              </span>
            </h2>
            <p className="mt-6 max-w-sm text-[15px] leading-relaxed text-ink-muted">
              If something here isn&rsquo;t covered, open an issue on the repo
              — we&rsquo;d rather be direct than handwave.
            </p>
          </Reveal>

          <Reveal delay={0.05} className="lg:col-span-8">
            <div className="divide-y divide-hairline border-y border-hairline">
              {items.map((item, i) => (
                <FaqRow key={item.q} item={item} initial={i === 0} />
              ))}
            </div>
          </Reveal>
        </div>
      </Container>
    </section>
  );
}

function FaqRow({ item, initial = false }: { item: QA; initial?: boolean }) {
  const [open, setOpen] = useState(initial);
  const prefersReduced = useReducedMotion();

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="group flex w-full items-center justify-between gap-6 py-6 text-left transition-colors hover:text-accent"
      >
        <span className="font-display text-[20px] font-normal leading-snug tracking-tight sm:text-[22px]">
          {item.q}
        </span>
        <span
          aria-hidden
          className="flex h-8 w-8 flex-none items-center justify-center rounded-full border border-hairline transition-colors group-hover:border-accent"
        >
          <motion.svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            animate={{ rotate: open ? 45 : 0 }}
            transition={{
              duration: prefersReduced ? 0 : 0.3,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            <path
              d="M6 1v10M1 6h10"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
            />
          </motion.svg>
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              duration: prefersReduced ? 0 : 0.35,
              ease: [0.22, 1, 0.36, 1],
            }}
            className="overflow-hidden"
          >
            <div className="max-w-2xl pb-6 pr-12 text-[15px] leading-relaxed text-ink-muted">
              {item.a}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
