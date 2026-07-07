/**
 * 5軸レーダーチャート（SVG・依存なし）。スコア 0〜100 を想定。
 */

export interface RadarAxis {
  label: string;
  value: number;
}

interface Props {
  axes: RadarAxis[];
  size?: number;
  maxValue?: number;
}

function polar(cx: number, cy: number, r: number, angle: number): [number, number] {
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
}

export default function RadarChart({ axes, size = 280, maxValue = 100 }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 44;
  const count = axes.length;
  const angleFor = (i: number) => (Math.PI * 2 * i) / count - Math.PI / 2;

  const grid = [0.25, 0.5, 0.75, 1].map((level) =>
    axes
      .map((_, i) => {
        const [x, y] = polar(cx, cy, radius * level, angleFor(i));
        return `${x},${y}`;
      })
      .join(" ")
  );

  const scorePts = axes
    .map((a, i) => {
      const ratio = Math.max(0, Math.min(1, a.value / maxValue));
      const [x, y] = polar(cx, cy, radius * ratio, angleFor(i));
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={size} height={size} role="img" aria-label="スコアレーダーチャート">
      {grid.map((pts, i) => (
        <polygon key={`g-${i}`} points={pts} fill="none" stroke="#e5e7eb" strokeWidth={1} />
      ))}
      {axes.map((a, i) => {
        const [x, y] = polar(cx, cy, radius, angleFor(i));
        const [lx, ly] = polar(cx, cy, radius + 22, angleFor(i));
        return (
          <g key={`a-${i}`}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="#e5e7eb" strokeWidth={1} />
            <text
              x={lx}
              y={ly}
              fontSize={12}
              fill="#6b7280"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {a.label}
            </text>
          </g>
        );
      })}
      <polygon points={scorePts} fill="rgba(15,111,255,0.25)" stroke="#0f6fff" strokeWidth={2} />
      {axes.map((a, i) => {
        const ratio = Math.max(0, Math.min(1, a.value / maxValue));
        const [x, y] = polar(cx, cy, radius * ratio, angleFor(i));
        return <circle key={`d-${i}`} cx={x} cy={y} r={3} fill="#0f6fff" />;
      })}
    </svg>
  );
}
