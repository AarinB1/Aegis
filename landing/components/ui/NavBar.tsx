import { LinkButton } from "./Button";
import { Container } from "./Container";
import { Wordmark } from "./Wordmark";

const links = [
  { label: "Features", href: "#features" },
  { label: "Ethics", href: "#ethics" },
  { label: "FAQ", href: "#faq" },
];

export function NavBar() {
  return (
    <header className="sticky top-0 z-30 border-b border-hairline/70 bg-paper/90 backdrop-blur">
      <Container className="flex items-center justify-between gap-6 py-5">
        <a href="#top" className="transition-opacity hover:opacity-80">
          <Wordmark />
        </a>

        <nav className="hidden items-center gap-7 md:flex">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted transition-colors hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <LinkButton
          href="https://github.com/AarinB1/Aegis"
          variant="secondary"
          className="hidden sm:inline-flex"
        >
          View Repo
        </LinkButton>
      </Container>
    </header>
  );
}
