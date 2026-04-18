# AEGIS Landing

Marketing landing page for AEGIS (AI-Enhanced Guidance for Integrated
Survival). Next.js 14 (App Router) + TypeScript + Tailwind CSS.

## Run locally

```bash
cd landing
npm install
npm run dev
```

The site serves at `http://localhost:3000`.

The primary CTA ("Launch Dashboard") points at `http://localhost:8501`,
which is where the bundled Streamlit dashboard serves when you run
`streamlit run ui/app.py` from the repo root.

## Build

```bash
npm run build
npm run start
```

## Structure

```
landing/
├── app/                      # Next.js App Router
│   ├── layout.tsx            # Root layout (fonts, metadata)
│   ├── page.tsx              # Landing page composition
│   └── globals.css           # Tailwind + design tokens
├── components/
│   ├── sections/             # Page sections (Hero, Features, etc.)
│   ├── ui/                   # Primitives (Button, NavBar, Reveal, …)
│   └── mocks/                # Composed SVG/HTML dashboard mockups
├── tailwind.config.ts        # Design tokens
└── package.json
```

## Fonts

All fonts load via `next/font/google`:

- Display: **Fraunces** (serif, tuned for clinical typography)
- Body / UI: **IBM Plex Sans**
- Numerals / code: **IBM Plex Mono** (tabular)

No CDN links, no external image hosts — all imagery is inline SVG or
composed HTML/CSS.
