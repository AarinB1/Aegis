import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`relative rounded-2xl border border-hairline bg-surface/70 p-6 shadow-panel transition-all duration-300 ease-damped hover:-translate-y-[1px] hover:shadow-panel-lg ${className}`}
    >
      {children}
    </div>
  );
}

export function PanelFrame({
  children,
  className = "",
  label,
}: {
  children: ReactNode;
  className?: string;
  label?: string;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-hairline bg-paper shadow-panel-lg ${className}`}
    >
      {label ? (
        <div className="flex items-center justify-between border-b border-hairline bg-surface/60 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
          <span>{label}</span>
          <span className="flex gap-1" aria-hidden>
            <span className="h-1.5 w-1.5 rounded-full bg-hairline" />
            <span className="h-1.5 w-1.5 rounded-full bg-hairline" />
            <span className="h-1.5 w-1.5 rounded-full bg-accent/70" />
          </span>
        </div>
      ) : null}
      <div>{children}</div>
    </div>
  );
}
