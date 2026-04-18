import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "var(--color-paper)",
        surface: "var(--color-surface)",
        ink: "var(--color-ink)",
        "ink-muted": "var(--color-ink-muted)",
        hairline: "var(--color-hairline)",
        accent: {
          DEFAULT: "var(--color-accent)",
          hover: "var(--color-accent-hover)",
        },
        triage: {
          red: "#C8342A",
          yellow: "#D4A017",
          green: "#2F7D3A",
          black: "#1A1A1A",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        "display-tight": "-0.035em",
      },
      fontVariantNumeric: {
        tabular: "tabular-nums",
      },
      boxShadow: {
        panel: "0 1px 0 rgba(10, 10, 10, 0.02), 0 0 0 1px rgba(10, 10, 10, 0.04)",
        "panel-lg":
          "0 1px 0 rgba(10, 10, 10, 0.02), 0 20px 40px -24px rgba(10, 10, 10, 0.18), 0 0 0 1px rgba(10, 10, 10, 0.05)",
      },
      transitionTimingFunction: {
        damped: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
