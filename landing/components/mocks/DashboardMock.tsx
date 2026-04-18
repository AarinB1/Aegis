type Casualty = {
  id: number;
  tag: "red" | "yellow" | "green" | "black";
  label: string;
  note: string;
  hr: string;
  rr: string;
  conf: number;
};

const casualties: Casualty[] = [
  {
    id: 7,
    tag: "red",
    label: "Arterial bleed · R thigh",
    note: "Tourniquet 11:04",
    hr: "132",
    rr: "28",
    conf: 94,
  },
  {
    id: 3,
    tag: "yellow",
    label: "Penetrating · L shoulder",
    note: "Airway clear",
    hr: "112",
    rr: "22",
    conf: 88,
  },
  {
    id: 5,
    tag: "red",
    label: "Stridor · suspected airway",
    note: "CLAP 0.87",
    hr: "—",
    rr: "34",
    conf: 87,
  },
  {
    id: 2,
    tag: "green",
    label: "Superficial lac · L arm",
    note: "Ambulatory",
    hr: "96",
    rr: "18",
    conf: 92,
  },
];

const tagColor: Record<Casualty["tag"], string> = {
  red: "#C8342A",
  yellow: "#D4A017",
  green: "#2F7D3A",
  black: "#1A1A1A",
};

const tagLabel: Record<Casualty["tag"], string> = {
  red: "IMMEDIATE",
  yellow: "DELAYED",
  green: "MINIMAL",
  black: "EXPECTANT",
};

export function DashboardMock() {
  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-hairline bg-paper shadow-panel-lg">
      {/* Top chrome */}
      <div className="flex items-center justify-between border-b border-hairline bg-surface/70 px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="relative inline-flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-triage-red/50" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-triage-red" />
            </span>
            LIVE
          </span>
          <span className="opacity-60">·</span>
          <span>MASCAL / GRID 38TKL 042 119</span>
        </div>
        <div className="hidden items-center gap-4 tabular md:flex">
          <span>
            MEDIC <span className="text-ink">SGT HAYES</span>
          </span>
          <span className="opacity-60">·</span>
          <span>
            UPLINK <span className="text-triage-green">OFFLINE ✓</span>
          </span>
        </div>
      </div>

      {/* Status counts */}
      <div className="grid grid-cols-4 divide-x divide-hairline border-b border-hairline bg-paper">
        <Counter tag="red" value={4} />
        <Counter tag="yellow" value={6} />
        <Counter tag="green" value={9} />
        <Counter tag="black" value={1} />
      </div>

      {/* Main split: video feed + roster */}
      <div className="grid grid-cols-12 gap-px bg-hairline">
        {/* Video feed */}
        <div className="col-span-12 bg-paper p-3 md:col-span-8">
          <VideoFeed />
        </div>

        {/* Roster */}
        <div className="col-span-12 bg-paper md:col-span-4">
          <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
            <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
              Casualty Roster
            </span>
            <span className="tabular font-mono text-[11px] text-ink-muted">
              20 tracked
            </span>
          </div>
          <ul className="divide-y divide-hairline">
            {casualties.map((c) => (
              <li
                key={c.id}
                className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-surface/60"
              >
                <span
                  aria-hidden
                  className="mt-1 inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: tagColor[c.tag] }}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="tabular font-mono text-xs text-ink-muted">
                      #{String(c.id).padStart(2, "0")}
                    </span>
                    <span
                      className="font-mono text-[10px] uppercase tracking-[0.14em]"
                      style={{ color: tagColor[c.tag] }}
                    >
                      {tagLabel[c.tag]}
                    </span>
                  </div>
                  <p className="truncate text-sm text-ink">{c.label}</p>
                  <p className="mt-0.5 truncate text-xs text-ink-muted">
                    {c.note} · HR {c.hr} · RR {c.rr}
                  </p>
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t border-hairline px-4 py-3 text-[11px] text-ink-muted">
            <span className="font-mono uppercase tracking-[0.14em]">
              Voice
            </span>{" "}
            <span className="tabular">&quot;Red tag 7&quot;</span>{" "}
            <span className="text-ink">→ IMMEDIATE assigned</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Counter({ tag, value }: { tag: Casualty["tag"]; value: number }) {
  return (
    <div className="flex items-baseline gap-2 px-4 py-3">
      <span
        aria-hidden
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: tagColor[tag] }}
      />
      <span className="tabular font-display text-2xl leading-none tracking-display-tight">
        {String(value).padStart(2, "0")}
      </span>
      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-muted">
        {tagLabel[tag]}
      </span>
    </div>
  );
}

function VideoFeed() {
  return (
    <div className="relative aspect-[16/10] w-full overflow-hidden rounded-lg bg-[#1a1a1a]">
      {/* Faux scene — warm gradient w/ sketched terrain */}
      <svg
        viewBox="0 0 800 500"
        className="absolute inset-0 h-full w-full"
        role="img"
        aria-label="Live video feed with bounding boxes"
      >
        <defs>
          <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3a3026" />
            <stop offset="60%" stopColor="#4a3a2a" />
            <stop offset="100%" stopColor="#2a251f" />
          </linearGradient>
          <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2f2820" />
            <stop offset="100%" stopColor="#1b1712" />
          </linearGradient>
          <pattern
            id="noise"
            width="3"
            height="3"
            patternUnits="userSpaceOnUse"
          >
            <rect width="3" height="3" fill="transparent" />
            <rect width="1" height="1" fill="rgba(255,255,255,0.03)" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="800" height="500" fill="url(#sky)" />
        <rect x="0" y="300" width="800" height="200" fill="url(#ground)" />
        <path
          d="M0 305 L120 280 L260 295 L400 275 L560 290 L720 268 L800 282 L800 310 L0 310 Z"
          fill="rgba(0,0,0,0.35)"
        />
        <rect x="0" y="0" width="800" height="500" fill="url(#noise)" />

        {/* Smoke wisps */}
        <g opacity="0.22" fill="#e6cfa8">
          <ellipse cx="180" cy="150" rx="120" ry="28" />
          <ellipse cx="520" cy="120" rx="180" ry="34" />
        </g>

        {/* Casualty figures (simple silhouettes) */}
        <Figure x={120} y={260} scale={1} />
        <Figure x={360} y={320} scale={0.9} prone />
        <Figure x={560} y={280} scale={0.8} />
        <Figure x={680} y={340} scale={0.7} prone />

        {/* Bounding boxes overlay */}
        <BBox
          x={78}
          y={232}
          w={108}
          h={132}
          color="#C8342A"
          id="07"
          tag="IMMEDIATE"
          conf={0.94}
        />
        <BBox
          x={300}
          y={286}
          w={140}
          h={96}
          color="#D4A017"
          id="03"
          tag="DELAYED"
          conf={0.88}
        />
        <BBox
          x={518}
          y={248}
          w={96}
          h={110}
          color="#C8342A"
          id="05"
          tag="IMMEDIATE"
          conf={0.87}
        />
        <BBox
          x={640}
          y={316}
          w={110}
          h={70}
          color="#2F7D3A"
          id="02"
          tag="MINIMAL"
          conf={0.92}
        />

        {/* HUD corners */}
        <g
          fontFamily="ui-monospace, SFMono-Regular, monospace"
          fontSize="11"
          fill="rgba(230,207,168,0.75)"
        >
          <text x="16" y="24">
            REC ● 00:04:12
          </text>
          <text x="16" y="42">
            YOLOv8 · ByteTrack · DINOv2
          </text>
          <text x="700" y="24" textAnchor="end">
            24.7 FPS
          </text>
          <text x="700" y="42" textAnchor="end">
            JETSON ORIN NX
          </text>
          <text x="16" y="488">
            re-ID: casualty #7 persistent across 312 frames
          </text>
        </g>

        {/* Reticle / crosshair center */}
        <g
          stroke="rgba(230,207,168,0.35)"
          strokeWidth="1"
          fill="none"
        >
          <circle cx="400" cy="250" r="14" />
          <line x1="400" y1="230" x2="400" y2="240" />
          <line x1="400" y1="260" x2="400" y2="270" />
          <line x1="380" y1="250" x2="390" y2="250" />
          <line x1="410" y1="250" x2="420" y2="250" />
        </g>
      </svg>
    </div>
  );
}

function Figure({
  x,
  y,
  scale = 1,
  prone = false,
}: {
  x: number;
  y: number;
  scale?: number;
  prone?: boolean;
}) {
  return (
    <g
      transform={`translate(${x}, ${y}) scale(${scale})${
        prone ? " rotate(78)" : ""
      }`}
      fill="#0e0c09"
      stroke="#6b5a43"
      strokeWidth="1"
      opacity="0.9"
    >
      <ellipse cx="0" cy="-50" rx="18" ry="20" />
      <path d="M-28 -28 Q0 -40 28 -28 L34 40 Q0 46 -34 40 Z" />
      <rect x="-30" y="36" width="18" height="52" rx="6" />
      <rect x="12" y="36" width="18" height="52" rx="6" />
    </g>
  );
}

function BBox({
  x,
  y,
  w,
  h,
  color,
  id,
  tag,
  conf,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  id: string;
  tag: string;
  conf: number;
}) {
  const labelW = 132;
  return (
    <g>
      {/* Corner brackets instead of full rect, clinical feel */}
      <g stroke={color} strokeWidth="1.6" fill="none">
        <path d={`M${x} ${y + 14} L${x} ${y} L${x + 14} ${y}`} />
        <path
          d={`M${x + w - 14} ${y} L${x + w} ${y} L${x + w} ${y + 14}`}
        />
        <path
          d={`M${x + w} ${y + h - 14} L${x + w} ${y + h} L${x + w - 14} ${
            y + h
          }`}
        />
        <path
          d={`M${x + 14} ${y + h} L${x} ${y + h} L${x} ${y + h - 14}`}
        />
      </g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        fill="none"
        stroke={color}
        strokeOpacity="0.22"
        strokeWidth="1"
      />
      {/* Label tag */}
      <g transform={`translate(${x}, ${y - 22})`}>
        <rect
          width={labelW}
          height="18"
          rx="2"
          fill={color}
          fillOpacity="0.92"
        />
        <text
          x="6"
          y="12"
          fontFamily="ui-monospace, SFMono-Regular, monospace"
          fontSize="10"
          fill="#fafaf7"
          letterSpacing="0.04em"
        >
          #{id} · {tag} · {conf.toFixed(2)}
        </text>
      </g>
    </g>
  );
}
