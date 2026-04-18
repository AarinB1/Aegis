"use client";

import { useEffect, useState } from "react";
import { LinkButton } from "./Button";
import { Wordmark } from "./Wordmark";

const links = [
  { href: "#features", label: "Features" },
  { href: "#ethics", label: "Ethics" },
  { href: "#faq", label: "FAQ" },
];

export function NavBar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={[
        "fixed inset-x-0 top-0 z-50 transition-colors duration-300 ease-damped",
        scrolled
          ? "border-b border-hairline bg-paper/85 backdrop-blur-md"
          : "border-b border-transparent bg-transparent",
      ].join(" ")}
    >
      <nav
        className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-10"
        aria-label="Primary"
      >
        <a href="#top" className="flex items-center">
          <Wordmark />
        </a>

        <ul className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="text-sm text-ink-muted transition-colors hover:text-ink"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2">
          <LinkButton
            href="http://localhost:8501"
            variant="primary"
            className="hidden sm:inline-flex"
          >
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
            href="http://localhost:8501"
            variant="primary"
            className="sm:hidden"
          >
            Launch
          </LinkButton>
        </div>
      </nav>
    </header>
  );
}
