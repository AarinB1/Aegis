import { PanelFrame } from "../ui/Card";

const nineLine = [
  { n: 1, label: "Location", value: "38TKL 042 119", filled: true },
  { n: 2, label: "Freq / callsign", value: "45.50 · DUSTOFF 3", filled: true },
  { n: 3, label: "Casualties by precedence", value: "A×2  B×1", filled: true },
  { n: 4, label: "Special equipment", value: "Ventilator", filled: true },
  { n: 5, label: "Casualties by type", value: "L×2  A×1", filled: true },
  { n: 6, label: "Security at PZ", value: "Possible enemy", filled: true },
  { n: 7, label: "Marking method", value: "IR strobe", filled: false },
  { n: 8, label: "Nationality / status", value: "US military", filled: true },
  { n: 9, label: "NBC contamination", value: "—", filled: false },
];

export function TriageMock() {
  return (
    <PanelFrame label="casualty #07 · expanded">
      <div className="grid grid-cols-1 divide-hairline lg:grid-cols-2 lg:divide-x">
        {/* Casualty card */}
        <div className="space-y-5 p-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
                <span className="inline-block h-2 w-2 rounded-full bg-triage-red" />
                IMMEDIATE · SALT
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <h4 className="font-display text-3xl font-normal tracking-display-tight">
                  Casualty #07
                </h4>
                <span className="tabular font-mono text-xs text-ink-muted">
                  11:04:22
                </span>
              </div>
            </div>
            <ConfBadge value={0.94} />
          </div>

          <div className="space-y-2 border-y border-hairline py-4">
            <Row label="Mechanism" value="Penetrating · R thigh" conf={0.91} />
            <Row label="Hemorrhage" value="Active · arterial" conf={0.94} />
            <Row label="Airway" value="Patent" conf={null} manual />
            <Row label="Respiration" value="28 br/min" conf={0.83} />
            <Row label="Pulse" value="132 bpm (radial)" conf={null} manual />
          </div>

          <div>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
              Interventions logged
            </span>
            <ul className="mt-2 space-y-1.5">
              <Intervention
                time="11:04"
                text="CAT tourniquet · R thigh proximal"
                who="medic"
              />
              <Intervention
                time="11:05"
                text="Airway clear · no occlusion"
                who="voice"
              />
              <Intervention
                time="11:06"
                text="MEDEVAC request generated"
                who="system"
              />
            </ul>
          </div>
        </div>

        {/* 9-line MEDEVAC */}
        <div className="bg-surface/40 p-5">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-muted">
              9-Line MEDEVAC
            </span>
            <span className="font-mono text-[11px] text-ink-muted">
              DRAFT · unconfirmed
            </span>
          </div>

          <ul className="mt-3 divide-y divide-hairline">
            {nineLine.map((l) => (
              <li
                key={l.n}
                className="grid grid-cols-[2rem_1fr_auto] items-center gap-3 py-2"
              >
                <span className="tabular font-mono text-xs text-ink-muted">
                  {String(l.n).padStart(2, "0")}
                </span>
                <div className="min-w-0">
                  <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
                    {l.label}
                  </div>
                  <div
                    className={`tabular truncate text-sm ${
                      l.filled ? "text-ink" : "text-ink-muted/60"
                    }`}
                  >
                    {l.filled ? l.value : "awaiting input"}
                  </div>
                </div>
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    l.filled ? "bg-triage-green" : "bg-hairline"
                  }`}
                  aria-hidden
                />
              </li>
            ))}
          </ul>

          <div className="mt-4 flex items-center justify-between gap-3 border-t border-hairline pt-4">
            <span className="font-mono text-[11px] text-ink-muted">
              Medic must confirm before send
            </span>
            <button
              type="button"
              className="rounded-full bg-accent px-3 py-1.5 text-xs font-medium text-paper transition-colors hover:bg-accent-hover"
            >
              Review &amp; confirm
            </button>
          </div>
        </div>
      </div>
    </PanelFrame>
  );
}

function Row({
  label,
  value,
  conf,
  manual,
}: {
  label: string;
  value: string;
  conf: number | null;
  manual?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-baseline gap-3">
        <span className="w-28 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
          {label}
        </span>
        <span className="text-sm text-ink">{value}</span>
      </div>
      {manual ? (
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
          medic · manual
        </span>
      ) : (
        <ConfBadge value={conf ?? 0} />
      )}
    </div>
  );
}

function ConfBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    pct >= 90
      ? "text-triage-green"
      : pct >= 75
      ? "text-accent"
      : "text-triage-yellow";
  return (
    <span
      className={`tabular inline-flex items-center gap-1.5 rounded-full border border-hairline bg-paper px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] ${tone}`}
    >
      <span
        className="inline-block h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: "currentColor" }}
        aria-hidden
      />
      AI · {pct}%
    </span>
  );
}

function Intervention({
  time,
  text,
  who,
}: {
  time: string;
  text: string;
  who: "medic" | "voice" | "system";
}) {
  const whoLabel = {
    medic: "MEDIC",
    voice: "VOICE",
    system: "SYSTEM",
  }[who];
  return (
    <li className="flex items-baseline gap-3 text-sm">
      <span className="tabular w-10 font-mono text-[11px] text-ink-muted">
        {time}
      </span>
      <span className="w-14 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
        {whoLabel}
      </span>
      <span className="flex-1 text-ink">{text}</span>
    </li>
  );
}
