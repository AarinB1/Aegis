import { ReactNode } from "react";

export function Overline({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted ${className}`}
    >
      <span
        aria-hidden
        className="inline-block h-px w-6 bg-ink-muted/40"
      />
      {children}
    </span>
  );
}
