/**
 * 総合スコアの推移を折れ線で表示する簡易チャート（SVG・依存なし）。
 */

interface Point {
  total_score: number;
  analyzed_at: string;
}

interface Props {
  history: Point[];
  width?: number;
  height?: number;
}

export default function ScoreHistoryChart({ history, width = 480, height = 160 }: Props) {
  if (history.length < 2) {
    return (
      <p style={{ color: "#6b7280", fontSize: 13 }}>履歴を表示するには2件以上の分析が必要です。</p>
    );
  }

  const pad = 28;
  const maxV = 100;
  const minV = 0;
  const n = history.length;
  const stepX = (width - pad * 2) / (n - 1);

  const toXY = (i: number, v: number): [number, number] => {
    const x = pad + stepX * i;
    const y = height - pad - ((v - minV) / (maxV - minV)) * (height - pad * 2);
    return [x, y];
  };

  const linePts = history.map((p, i) => toXY(i, p.total_score).join(",")).join(" ");

  return (
    <svg width={width} height={height} role="img" aria-label="総合スコア推移">
      {/* 目盛り線 0/50/100 */}
      {[0, 50, 100].map((v) => {
        const [, y] = toXY(0, v);
        return (
          <g key={v}>
            <line x1={pad} y1={y} x2={width - pad} y2={y} stroke="#eee" strokeWidth={1} />
            <text x={4} y={y + 4} fontSize={10} fill="#9ca3af">
              {v}
            </text>
          </g>
        );
      })}
      <polyline points={linePts} fill="none" stroke="#0f6fff" strokeWidth={2} />
      {history.map((p, i) => {
        const [x, y] = toXY(i, p.total_score);
        return <circle key={i} cx={x} cy={y} r={3} fill="#0f6fff" />;
      })}
    </svg>
  );
}
