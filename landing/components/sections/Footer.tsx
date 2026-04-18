import { Container } from "../ui/Container";
import { Wordmark } from "../ui/Wordmark";

const columns = [
  {
    heading: "Project",
    links: [
      { label: "Features", href: "#features" },
      { label: "Ethics", href: "#ethics" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "GitHub", href: "https://github.com/aarinb1/aegis" },
      { label: "README", href: "https://github.com/aarinb1/aegis#readme" },
      {
        label: "Architecture",
        href: "https://github.com/aarinb1/aegis/tree/main/docs",
      },
    ],
  },
  {
    heading: "Team",
    links: [
      {
        label: "About",
        href: "https://github.com/aarinb1/aegis#team",
      },
      {
        label: "Contact",
        href: "https://github.com/aarinb1/aegis/issues",
      },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-hairline bg-paper py-16">
      <Container>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <Wordmark />
            <p className="mt-4 max-w-sm text-sm italic leading-relaxed text-ink-muted">
              A shield of perception for those who shield others.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:grid-cols-3 lg:col-span-7">
            {columns.map((col) => (
              <div key={col.heading}>
                <h4 className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted">
                  {col.heading}
                </h4>
                <ul className="mt-4 space-y-2.5 text-sm">
                  {col.links.map((l) => (
                    <li key={l.label}>
                      <a
                        href={l.href}
                        className="text-ink transition-colors hover:text-accent"
                      >
                        {l.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-14 flex flex-col gap-2 border-t border-hairline pt-6 text-[12px] text-ink-muted sm:flex-row sm:items-center sm:justify-between">
          <span className="tabular">
            © {new Date().getFullYear()} AEGIS · MIT License
          </span>
          <span className="font-mono uppercase tracking-[0.14em]">
            Built for the medic on the ground.
          </span>
        </div>
      </Container>
    </footer>
  );
}
