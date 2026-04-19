# AEGIS Landing

Marketing landing page for AEGIS, built with Next.js 14, TypeScript, and
Tailwind CSS.

## Run locally

```bash
cd landing
npm install
npm run dev
```

By default, Next serves locally on `http://localhost:3000` unless you pass a
different port.

## Dashboard link behavior

The landing page’s primary CTA opens the Streamlit dashboard on
`http://localhost:8501` in the current committed build.

If your local dashboard is running on a different port, update the CTA target
in:

- `components/sections/Hero.tsx`
- `components/ui/NavBar.tsx`

## Build

```bash
npm run build
npm run start
```

## Structure

```text
landing/
├── app/                      # App Router entrypoints and global styles
├── components/
│   ├── mocks/                # Inline dashboard / system mockups
│   ├── sections/             # Hero, features, ethics, FAQ, footer
│   └── ui/                   # Shared UI primitives
├── package.json
├── postcss.config.js
└── tailwind.config.ts
```

