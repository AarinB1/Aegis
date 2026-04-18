export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-baseline gap-1.5 font-display text-[1.35rem] font-medium tracking-display-tight text-ink ${className}`}
      aria-label="AEGIS"
    >
      <span
        aria-hidden
        className="inline-block h-2 w-2 -translate-y-[2px] rotate-45 rounded-[1px] bg-accent"
      />
      AEGIS
    </span>
  );
}
