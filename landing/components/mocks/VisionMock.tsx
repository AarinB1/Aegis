import { PanelFrame } from "../ui/Card";

export function VisionMock() {
  return (
    <PanelFrame label="vision · frame 00:04:12">
      <div className="relative aspect-[5/4] w-full bg-[#1a1612]">
        <svg
          viewBox="0 0 500 400"
          className="absolute inset-0 h-full w-full"
          role="img"
          aria-label="Vision pipeline frame with wound segmentation overlay"
        >
          <defs>
            <linearGradient id="vg-bg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3e3227" />
              <stop offset="100%" stopColor="#1d1712" />
            </linearGradient>
            <radialGradient id="vg-focus" cx="0.55" cy="0.55" r="0.5">
              <stop offset="0%" stopColor="rgba(255,230,190,0.25)" />
              <stop offset="100%" stopColor="transparent" />
            </radialGradient>
            <pattern
              id="vg-scan"
              width="1"
              height="3"
              patternUnits="userSpaceOnUse"
            >
              <rect width="1" height="1" fill="rgba(255,255,255,0.03)" />
            </pattern>
          </defs>

          <rect width="500" height="400" fill="url(#vg-bg)" />
          <rect width="500" height="400" fill="url(#vg-scan)" />
          <rect width="500" height="400" fill="url(#vg-focus)" />

          {/* Subject torso silhouette */}
          <g transform="translate(250 210)" opacity="0.92">
            <path
              d="M-120 -150 Q0 -180 120 -150 L150 120 Q0 160 -150 120 Z"
              fill="#2a2118"
              stroke="#6b553a"
              strokeWidth="1"
            />
            {/* Uniform seam */}
            <line
              x1="0"
              y1="-160"
              x2="0"
              y2="140"
              stroke="#5a4632"
              strokeWidth="1"
              strokeOpacity="0.6"
            />
          </g>

          {/* Wound segmentation mask — irregular blob */}
          <g transform="translate(200 170)">
            <path
              d="M0 0 Q16 -14 34 -6 Q52 3 58 20 Q60 38 42 46 Q22 52 6 44 Q-12 36 -10 16 Q-8 4 0 0 Z"
              fill="#C8342A"
              fillOpacity="0.32"
              stroke="#C8342A"
              strokeWidth="1.4"
              strokeDasharray="4 3"
            />
            {/* Measurement crosshair on wound */}
            <line
              x1="-18"
              y1="22"
              x2="66"
              y2="22"
              stroke="#D4A017"
              strokeWidth="1"
              strokeDasharray="2 2"
            />
            <text
              x="70"
              y="26"
              fontFamily="ui-monospace, SFMono-Regular, monospace"
              fontSize="10"
              fill="#D4A017"
            >
              8.2 cm
            </text>
          </g>

          {/* Bounding box around person */}
          <g stroke="#C8342A" strokeWidth="1.4" fill="none">
            <path d="M104 54 L104 40 L118 40" />
            <path d="M382 40 L396 40 L396 54" />
            <path d="M396 346 L396 360 L382 360" />
            <path d="M118 360 L104 360 L104 346" />
          </g>
          <rect
            x="104"
            y="40"
            width="292"
            height="320"
            fill="none"
            stroke="#C8342A"
            strokeOpacity="0.16"
            strokeWidth="1"
          />

          {/* Labels */}
          <g fontFamily="ui-monospace, SFMono-Regular, monospace" fontSize="10">
            <rect x="104" y="18" width="180" height="18" fill="#C8342A" />
            <text x="110" y="30" fill="#fafaf7" letterSpacing="0.04em">
              CASUALTY #07 · 0.94
            </text>

            <rect x="196" y="140" width="104" height="16" fill="#0a0a0a" fillOpacity="0.7" />
            <text x="202" y="152" fill="#D4A017">
              wound · 0.87 · hemorrhage
            </text>

            <rect x="380" y="374" width="112" height="18" fill="#0a0a0a" fillOpacity="0.7" />
            <text x="386" y="386" fill="#e6cfa8">
              re-ID: casualty #7
            </text>
          </g>

          {/* HUD */}
          <g
            fontFamily="ui-monospace, SFMono-Regular, monospace"
            fontSize="10"
            fill="rgba(230,207,168,0.72)"
          >
            <text x="14" y="22">
              YOLOv8 · ByteTrack
            </text>
            <text x="14" y="38">
              MobileSAM · Grounding DINO
            </text>
            <text x="486" y="22" textAnchor="end">
              24.7 fps
            </text>
          </g>

          {/* Pose skeleton keypoints */}
          <g fill="#D4A017" opacity="0.85">
            <circle cx="250" cy="74" r="2" />
            <circle cx="226" cy="140" r="2" />
            <circle cx="274" cy="140" r="2" />
            <circle cx="210" cy="220" r="2" />
            <circle cx="290" cy="220" r="2" />
            <circle cx="232" cy="300" r="2" />
            <circle cx="268" cy="300" r="2" />
          </g>
          <g
            stroke="#D4A017"
            strokeOpacity="0.5"
            strokeWidth="1"
            fill="none"
          >
            <path d="M250 74 L226 140 L210 220 L232 300" />
            <path d="M250 74 L274 140 L290 220 L268 300" />
            <path d="M226 140 L274 140" />
          </g>
        </svg>
      </div>

      <div className="grid grid-cols-3 divide-x divide-hairline border-t border-hairline bg-surface/50 text-[11px] uppercase tracking-[0.14em] text-ink-muted">
        <Stat label="Detect" value="24.7" unit="fps" />
        <Stat label="Segment" value="0.87" unit="conf" />
        <Stat label="Re-ID" value="312" unit="frames" />
      </div>
    </PanelFrame>
  );
}

function Stat({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div className="flex flex-col gap-0.5 px-4 py-3 font-mono">
      <span>{label}</span>
      <span className="tabular font-display text-lg font-normal normal-case tracking-display-tight text-ink">
        {value}{" "}
        <span className="font-mono text-[10px] tracking-[0.14em] text-ink-muted">
          {unit}
        </span>
      </span>
    </div>
  );
}
