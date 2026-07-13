/**
 * 複数シリーズ対応レーダーチャート（SVG・依存なし）。
 * 選手の横並び比較(C#21)で、複数選手のスコアを重ねて表示する。
 */

export interface RadarSeries {
  name: string;
  color: string;
  values: number[]; // axes と同順・同数
}

interface Props {
  axisLabels: string[];
  series: RadarSeries[];
  size?: number;
  maxValue?: number;
}

function polar(cx: number, cy: number, r: number, angle: number): [number, number] {
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
}

export default function MultiRadarChart({ axisLabels, series, size = 340, maxValue = 100 }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 52;
  const count = axisLabels.length;
  const angleFor = (i: number) => (Math.PI * 2 * i) / count - Math.PI / 2;

  const grid = [0.25, 0.5, 0.75, 1].map((level) =>
    axisLabels
      .map((_, i) => {
        const [x, y] = polar(cx, cy, radius * level, angleFor(i));
        return `${x},${y}`;
      })
      .join(" ")
  );

  const polygonFor = (values: number[]) =>
    values
      .map((v, i) => {
        const ratio = Math.max(0, Math.min(1, v / maxValue));
        const [x, y] = polar(cx, cy, radius * ratio, angleFor(i));
        return `${x},${y}`;
      })
      .join(" ");

  return (
    <svg width={size} height={size} role="img" aria-label="選手比較レーダーチャート">
      {grid.map((pts, i) => (
        <polygon key={`g-${i}`} points={pts} fill="none" stroke="#e5e7eb" strokeWidth={1} />
      ))}
      {axisLabels.map((label, i) => {
        const [x, y] = polar(cx, cy, radius, angleFor(i));
        const [lx, ly] = polar(cx, cy, radius + 26, angleFor(i));
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
              {label}
            </text>
          </g>
        );
      })}
      {series.map((s) => (
        <polygon
          key={s.name}
          points={polygonFor(s.values)}
          fill="none"
          stroke={s.color}
          strokeWidth={2}
          opacity={0.9}
        />
      ))}
    </svg>
  );
}
