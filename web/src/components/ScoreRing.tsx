/**
 * 円形スコアゲージ（SVG・依存なし）。スコア 0〜100 を弧で表現する。
 */

interface Props {
  value: number;
  size?: number;
  stroke?: number;
}

function colorFor(v: number): string {
  if (v >= 75) return "#16a34a";
  if (v >= 55) return "#2563eb";
  if (v >= 40) return "#d97706";
  return "#dc2626";
}

export default function ScoreRing({ value, size = 56, stroke = 5 }: Props) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, value));
  const dash = (clamped / 100) * circ;

  return (
    <svg width={size} height={size} role="img" aria-label={`スコア ${clamped}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e6e9f0" strokeWidth={stroke} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={colorFor(clamped)}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circ - dash}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  );
}
