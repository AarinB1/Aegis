import { PanelFrame } from "../ui/Card";

// Deterministic pseudo-waveform values so SSR and CSR match.
const waveform = [
  6, 10, 14, 8, 12, 18, 22, 16, 10, 6, 8, 12, 20, 28, 36, 44, 40, 30, 22, 16,
  12, 10, 14, 20, 18, 14, 12, 10, 14, 18, 22, 26, 30, 26, 20, 14, 10, 8, 12, 16,
  20, 18, 14, 12, 16, 22, 30, 38, 46, 52, 58, 54, 46, 38, 30, 24, 18, 14, 16,
  20, 26, 32, 28, 22, 16, 12, 10, 14, 18, 20, 18, 14, 10, 8, 12, 16, 22, 28, 24,
  18, 14, 10, 12, 16, 20, 18, 14, 10,
];

export function AudioMock() {
  const flagStart = 44; // stridor flagged region
  const flagEnd = 60;

  return (
    <PanelFrame label="audio · 00:00:06.4">
      <div className="space-y-0 divide-y divide-hairline">
        {/* Waveform */}
        <div className="relative px-5 py-6">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-triage-red" />
              Stridor detected
              <span className="text-ink">· 0.87</span>
            </div>
            <span className="tabular font-mono text-[11px] text-ink-muted">
              CLAP zero-shot
            </span>
          </div>

          <svg
            viewBox="0 0 440 96"
            className="h-24 w-full"
            role="img"
            aria-label="Audio waveform with flagged stridor section"
          >
            {/* Center axis */}
            <line
              x1="0"
              y1="48"
              x2="440"
              y2="48"
              stroke="rgba(10,10,10,0.1)"
              strokeDasharray="2 3"
            />
            {/* Flagged region */}
            <rect
              x={flagStart * 5}
              y="4"
              width={(flagEnd - flagStart) * 5}
              height="88"
              fill="#C8342A"
              fillOpacity="0.07"
              stroke="#C8342A"
              strokeOpacity="0.3"
              strokeDasharray="3 3"
            />
            {waveform.map((v, i) => {
              const inFlag = i >= flagStart && i <= flagEnd;
              const x = i * 5 + 2;
              const h = v;
              return (
                <rect
                  key={i}
                  x={x}
                  y={48 - h}
                  width="2.4"
                  height={h * 2}
                  rx="1"
                  fill={inFlag ? "#C8342A" : "#0a0a0a"}
                  opacity={inFlag ? 0.95 : 0.58}
                />
              );
            })}
          </svg>

          <div className="mt-2 flex justify-between font-mono text-[10px] text-ink-muted">
            <span>00:00.0</span>
            <span>00:03.2</span>
            <span>00:06.4</span>
          </div>
        </div>

        {/* Respiratory readouts */}
        <div className="grid grid-cols-3 divide-x divide-hairline">
          <Readout label="Resp rate" value="34" unit="br/min" tone="red" />
          <Readout label="Pattern" value="Irregular" tone="yellow" />
          <Readout label="Pulse ox" value="—" unit="spO₂" />
        </div>

        {/* Voice transcript */}
        <div className="space-y-3 px-5 py-5">
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
              <path
                d="M6 1a2 2 0 0 0-2 2v3a2 2 0 1 0 4 0V3a2 2 0 0 0-2-2Zm-4 5a4 4 0 0 0 8 0M6 10v1"
                stroke="currentColor"
                strokeWidth="1.2"
                fill="none"
                strokeLinecap="round"
              />
            </svg>
            Whisper · transcript
          </div>
          <TranscriptLine
            time="03.1"
            who="MEDIC"
            text={
              <>
                <span className="rounded bg-accent/12 px-1.5 py-0.5 text-ink ring-1 ring-inset ring-accent/30">
                  red tag 7
                </span>
              </>
            }
          />
          <div className="flex items-center gap-2 pl-12 font-mono text-[11px] text-ink-muted">
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
              <path
                d="M2 2v6l6-3z"
                fill="currentColor"
              />
            </svg>
            parsed intent
            <span className="tabular">set_triage(id=7, tag=IMMEDIATE)</span>
          </div>
          <TranscriptLine
            time="03.4"
            who="AEGIS"
            text={
              <span className="text-ink">
                IMMEDIATE assigned to casualty 7 · confirm?
              </span>
            }
          />
        </div>
      </div>
    </PanelFrame>
  );
}

function Readout({
  label,
  value,
  unit,
  tone,
}: {
  label: string;
  value: string;
  unit?: string;
  tone?: "red" | "yellow";
}) {
  const toneColor =
    tone === "red"
      ? "text-triage-red"
      : tone === "yellow"
      ? "text-triage-yellow"
      : "text-ink";
  return (
    <div className="flex flex-col gap-0.5 px-5 py-4">
      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
        {label}
      </span>
      <span
        className={`tabular font-display text-2xl font-normal leading-none tracking-display-tight ${toneColor}`}
      >
        {value}
        {unit ? (
          <span className="ml-1 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
            {unit}
          </span>
        ) : null}
      </span>
    </div>
  );
}

function TranscriptLine({
  time,
  who,
  text,
}: {
  time: string;
  who: string;
  text: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-3 font-mono text-sm">
      <span className="tabular w-10 text-[11px] text-ink-muted">{time}</span>
      <span className="w-14 text-[11px] uppercase tracking-[0.14em] text-ink-muted">
        {who}
      </span>
      <span className="flex-1 font-sans">{text}</span>
    </div>
  );
}
